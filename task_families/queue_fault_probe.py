"""Inject verifier faults into disposable copies, never an admitted source capsule.
Run on a trusted controller with PB_CONFIG pointing to the licensed backend.
Raw output is private; summary exposes only classifications and source hashes.
"""
import argparse, hashlib, json, os, shutil, subprocess, sys, time
from pathlib import Path
from task_families.package import verify


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(package, out):
    package, out = Path(package).resolve(), Path(out).resolve()
    manifest = verify(package)
    if manifest.get('family') != 'x2p_retirement_queues_v1':
        raise ValueError('Expected queue family capsule')
    config = Path(os.environ.get('PB_CONFIG', Path.cwd()/'.local/config.json')).resolve()
    if not config.is_file():
        raise ValueError('Trusted backend configuration required')
    out.mkdir(parents=True, exist_ok=False)
    results = {}
    for name in ('ordinary_candidate', 'early_retirement_oracle', 'missing_ledger_hook'):
        root = out/name/'source'; root.mkdir(parents=True)
        for entry in manifest['files']:
            target = root/entry; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(str(package/entry), str(target))
        changed = None
        if name == 'early_retirement_oracle':
            changed = root/'verifier/task003/scoreboard.sv'
            old = 'apb_completed=1;response_age=0;'
            new = old+'\n   if(expected.xact_type==svt_axi_transaction::WRITE) begin id=aq.pop_front();id=wq.pop_front();end'
        elif name == 'missing_ledger_hook':
            changed = root/'verifier/task003/tb.sv'
            old, new = 'sb.before_edge();family_check();', 'sb.before_edge();'
        if changed:
            text = changed.read_text()
            if text.count(old) != 1: raise ValueError('Injection anchor changed')
            changed.write_text(text.replace(old,new))
        candidate = root/'fixtures/task003'/('reference.sv' if name=='missing_ledger_hook' else 'bad_early_credit.sv')
        started = time.time()
        with (out/name/'controller.log').open('w') as log:
            child = subprocess.run([sys.executable,'-m','verifier.task003.campaign',str(candidate),str(out/name/'grade'),'--public','--case','intake_b_stall'],cwd=str(root),env=dict(os.environ,PB_CONFIG=str(config)),stdout=log,stderr=subprocess.STDOUT)
        verdict = json.loads((out/name/'grade/result.json').read_text())
        logs = '\n'.join(p.read_text(errors='replace') for p in (out/name/'grade').rglob('simulation.log'))
        results[name] = {'reward':verdict['reward'],'category':verdict['category'],
                         'candidate_sha256':sha(candidate),'result_sha256':sha(out/name/'grade/result.json'),
                         'changed_file':str(changed.relative_to(root)) if changed else None,
                         'changed_sha256':sha(changed) if changed else None,
                         'wall_seconds':time.time()-started,'controller_exit':child.returncode,
                         'ledger_disagreement_observed':'Independent retirement ledger disagrees' in logs,
                         'ledger_execution_marker':'PBQ_LEDGER_EXECUTED' in logs,
                         'simulation_done':'PBQ_DONE' in logs}
        (out/'progress.json').write_text(json.dumps(results,indent=2)+'\n')
        current = results[name]
        expected = (current['reward']==0 if name=='ordinary_candidate' else
                    current['reward'] is None and current['category']=='infrastructure_error' and
                    (current['ledger_disagreement_observed'] if name=='early_retirement_oracle' else
                     current['simulation_done'] and not current['ledger_execution_marker']))
        if not expected:
            result={'schema':'queue-verifier-fault-probe-v1','accepted':False,'stopped_after':name,
                    'manifest_sha256':sha(package/'family-manifest.json'),'probe_sha256':sha(__file__),
                    'results':results,'scope':'Unexpected probe result; preserve evidence and stop subsequent tool calls.'}
            (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
            return result
    a,b,c = [results[n] for n in ('ordinary_candidate','early_retirement_oracle','missing_ledger_hook')]
    accepted = (a['reward']==0 and a['candidate_sha256']==b['candidate_sha256'] and
                b['reward'] is None and b['category']=='infrastructure_error' and b['ledger_disagreement_observed'] and
                c['reward'] is None and c['category']=='infrastructure_error' and c['simulation_done'] and not c['ledger_execution_marker'])
    result={'schema':'queue-verifier-fault-probe-v1','accepted':accepted,'manifest_sha256':sha(package/'family-manifest.json'),
            'probe_sha256':sha(__file__),'results':results,
            'scope':'Controlled verifier faults on copies; not an observed historical false PASS. Same erroneous candidate with ordinary and deliberately corrupted oracle. Missing-hook uses a legal reference.'}
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('package');p.add_argument('out');a=p.parse_args()
    r=run(a.package,a.out);print(json.dumps(r,indent=2));raise SystemExit(0 if r['accepted'] else 1)
