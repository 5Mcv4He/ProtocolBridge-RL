"""Qualify exact stopped-episode inputs, reusing only identical admitted evidence.
This research-side operation never changes model rewards or sends observations.
The output contains private inputs/logs; keep it in trusted ignored storage.
"""
import argparse, hashlib, json, os, subprocess, sys, time
from pathlib import Path
from task_families.package import verify
from task_families.report import report
from scripts.verify_experiment_inputs import frozen_inputs
from environment.remote_backend import toolchain_metadata


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def check_binding(capsule, admission, experiment):
    if experiment['task_id']!=capsule['task_id'] or experiment['toolchain']!=admission['toolchain']:
        raise ValueError('Task/toolchain differs')
    expected={k:v for k,v in capsule['files'].items() if k.split('/')[0] in ('environment','verifier','fixtures','tasks','tests')}
    if experiment.get('protocol')=='text-json-atomic-v2':
        for name in ('analyze_policy.py','audit_policy.py','batch_analysis.py','batch_tables.py'):
            key='scripts/'+name;expected[key]=capsule['files'][key]
    if not expected or experiment.get('source_files')!=expected:
        raise ValueError('Episode source differs from admitted capsule')


def qualify(package,gate,episodes,out):
    package,gate,out=map(lambda p:Path(p).resolve(),(package,gate,out))
    capsule=verify(package);admission=report(package,gate)
    config=Path(os.environ.get('PB_CONFIG',Path.cwd()/'.local/config.json')).resolve()
    if toolchain_metadata(json.loads(config.read_text()))!=admission['toolchain']:
        raise ValueError('Configured toolchain differs from admission')
    unique={};bindings=[]
    for episode in episodes:
        episode=Path(episode).resolve();m,inputs=frozen_inputs(episode)
        check_binding(capsule,admission,m)
        for trial in m['schedule']:
            state=json.loads((episode/(trial['id']+'-job.json')).read_text())
            if state['status']!='finished' or not (episode/trial['id']/'metrics.json').is_file():
                raise ValueError('Episode not complete; do not qualify active inputs')
        for item in inputs:unique.setdefault(item['sha256'],item['path'])
        bindings.append({'experiment_sha256':sha(episode/'experiment.json'),'input_hashes':{x['name']:x['sha256'] for x in inputs}})
    out.mkdir(parents=True,exist_ok=False)
    meta=json.loads((package/'tasks'/capsule['task_id']/'task.json').read_text())
    reference=package/meta['quality']['references'][0];prior=gate/Path(meta['quality']['references'][0]).stem
    prior_raw=json.loads((prior/'result.json').read_text());prior_hash=sha(prior/'cases.json')
    if prior_raw['suite_sha256']!=prior_hash or prior_raw['reward']!=1 or not prior_raw['verification_complete']:
        raise ValueError('Prior reference input not fully verified')
    freeze={'schema':'family-input-qualification-v1','task_id':capsule['task_id'],
            'qualifier_sha256':sha(__file__),'manifest_sha256':sha(package/'family-manifest.json'),
            'gate_result_sha256':sha(gate/'result.json'),'reference_sha256':sha(reference),
            'toolchain':admission['toolchain'],'cohorts':bindings}
    (out/'freeze.json').write_text(json.dumps(freeze,indent=2)+'\n')
    results={};reuse=None
    for digest,path in sorted(unique.items()):
        if digest==prior_hash:
            r=prior_raw;mode='reused_exact_admitted_input';result_hash=sha(prior/'result.json')
        else:
            dest=out/('input-'+digest[:16]);started=time.monotonic()
            command=[sys.executable,'-m',meta['verifier'],str(reference),str(dest),'--cases-file',str(path)]
            if reuse:command+=['--reuse',str(reuse)]
            with (out/(digest[:16]+'.log')).open('w') as log:
                proc=subprocess.run(command,cwd=str(package),env=dict(os.environ,PB_CONFIG=str(config)),stdout=log,stderr=subprocess.STDOUT)
            r=json.loads((dest/'result.json').read_text());mode='new_positive_control_simulation';result_hash=sha(dest/'result.json')
            if (dest/'backend.json').exists():reuse=dest
            if r['source_sha256']!=sha(reference):raise ValueError('Positive-control source mismatch')
        results[digest]={'mode':mode,'reward':r['reward'],'category':r['category'],'verification_complete':r['verification_complete'],
                         'suite_sha256':r['suite_sha256'],'result_sha256':result_hash,'planned':r.get('planned'),
                         'checked':r.get('checked'),'aborted':r.get('aborted'),
                         'new_run_wall_seconds':time.monotonic()-started if mode=='new_positive_control_simulation' else 0,
                         'prior_control':prior.name if mode=='reused_exact_admitted_input' else None}
        (out/'progress.json').write_text(json.dumps(results,indent=2)+'\n')
        if r['reward']!=1 or not r['verification_complete'] or r['suite_sha256']!=digest:break
    result={'schema':'family-input-qualification-v1','accepted':len(results)==len(unique) and all(r['reward']==1 and r['verification_complete'] and r['suite_sha256']==h for h,r in results.items()),
            'freeze_sha256':sha(out/'freeze.json'),'results':results,
            'scope':'Exact stopped-episode inputs and admitted source/toolchain binding. Reused entries are prior real positive-control evidence, not new simulation; new entries run the same frozen reference. Candidate rewards and solver observations remain untouched.'}
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('package');p.add_argument('gate');p.add_argument('out');p.add_argument('episodes',nargs='+');a=p.parse_args()
    r=qualify(a.package,a.gate,a.episodes,a.out);print(json.dumps(r,indent=2));raise SystemExit(0 if r['accepted'] else 1)
