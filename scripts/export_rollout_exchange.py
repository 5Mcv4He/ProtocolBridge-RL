"""Auditable tool-trajectory exchange from reviewed publications; no private raw inputs.
This is data readiness, not an on-policy trainer: model tokens/log-probabilities
are unavailable and unselected traces remain explicitly absent.
"""
import argparse,hashlib,json,re,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'))
def safe(root,name):
    p=Path(name)
    if p.is_absolute() or '..' in p.parts:raise ValueError('Unsafe evidence path')
    value=(root/p).resolve()
    try:value.relative_to(root.resolve())
    except ValueError:raise ValueError('Evidence path escapes source')
    return value

def validate_source(root):
    root=Path(root);pub=json.loads((root/'publication.json').read_text())
    for n,h in pub['files'].items():
        if sha(safe(root,n))!=h:raise ValueError('Publication integrity failure: '+n)
    audit=json.loads((root/'audit.json').read_text())
    if not audit.get('accepted'):raise ValueError('Source trajectory audit did not pass')
    manifest=json.loads((root/'experiment.json').read_text());analysis=json.loads((root/'batch-analysis.json').read_text())
    rows=analysis['rows'];ids=[r['trial'] for r in rows]
    if len(set(ids))!=len(ids):raise ValueError('Duplicate trial row')
    planned={x['id'] for x in manifest['schedule']}
    if not set(ids)<=planned:raise ValueError('Outcome outside frozen schedule')
    provenance={r['trial']:r for r in json.loads((root/'all-trial-provenance.json').read_text())['trials']}
    feedback={r['trial']:r for r in json.loads((root/'feedback-history.json').read_text())['trials']}
    if set(provenance)!=set(ids) or set(feedback)!=set(ids):raise ValueError('Incomplete all-trial provenance')
    if pub.get('all_started_trials')!=len(rows):raise ValueError('Started denominator mismatch')
    for r in rows:
        if r['reward'] not in (0,1,None) or provenance[r['trial']]['reward']!=r['reward']:raise ValueError('Reward/provenance mismatch')
    return manifest,rows,provenance,feedback

def training_infrastructure(row,public_events):
    # Analysis rows also flag held-out/post-hoc failures. Those must not become
    # training-side validity signals or alter the terminal reward.
    return row['terminal_category']=='infrastructure_error' or any(e['observation']['status']=='ENV_ERROR' for e in public_events)

def export(sources,out,schema_version=1):
    if schema_version not in (1,2):raise ValueError('Unsupported exchange schema')
    sources=[Path(p).resolve() for p in sources]
    if len(set(sources))!=len(sources):raise ValueError('Duplicate source publication')
    validated=[validate_source(p) for p in sources]
    for manifest,_,_,_ in validated:
        cap=manifest.get('capabilities')
        if cap not in (None,'engineering-tools-v1'):raise ValueError('Unknown capability contract')
        if cap and schema_version!=2:raise ValueError('Engineering observations require exchange schema 2')
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    for d in ('training','evaluation','analysis','artifacts'):(out/d).mkdir()
    records=[];evaluations=[];offline=[];keys=set();source_rows=[]
    def artifact(source):
        h=sha(source);name='artifacts/'+h+source.suffix;dest=out/name
        if not dest.exists():shutil.copyfile(str(source),str(dest))
        return {'sha256':h,'file':name}
    for root,(m,rows,provenance,feedback) in zip(sources,validated):
        cohort=sha(root/'experiment.json');task=m.get('task_id','axil_to_apb4_001')
        metadata='tasks/'+task+('/task.yaml' if task=='axil_to_apb4_001' else '/task.json')
        task_version=None;mp=ROOT/metadata
        if mp.exists() and sha(mp)==m['source_files'].get(metadata):
            task_version=int(re.search(r'^version:\s*(\d+)',mp.read_text(),re.M).group(1)) if metadata.endswith('.yaml') else json.loads(mp.read_text())['version']
        verifier_hash=hashlib.sha256(canonical({k:v for k,v in m['source_files'].items() if k.startswith('verifier/')}).encode()).hexdigest()
        source_rows.append({'experiment_sha256':cohort,'publication_sha256':sha(root/'publication.json'),'started_trials':len(rows),'study':m.get('study'),'task_id':task})
        for row in rows:
            name=row['trial'];key=cohort+':'+name
            if key in keys:raise ValueError('Duplicate episode identity')
            keys.add(key);d=safe(root,name);prov=provenance[name];events=None;final=None
            if (d/'trace.json').exists():
                trace=json.loads((d/'trace.json').read_text());events=[]
                for e in trace:
                    action=e['action'];a={k:action[k] for k in ('tool','file','content_sha256') if k in action}
                    candidate=action.get('candidate_file')
                    if candidate:
                        path=safe(d,candidate)
                        if sha(path)!=action.get('content_sha256'):raise ValueError('Edit artifact mismatch')
                        a['content_artifact']=artifact(path)
                    # Already projected public observations only. No grader result is merged.
                    obs=e['observation'];allowed={'status','reason','instruction','action_fields','file','content_sha256','content_bytes','remaining_test_calls','category','first_failed_case','diagnostic'}
                    if schema_version==2 and m.get('capabilities')=='engineering-tools-v1':
                        if action.get('tool')=='compile':allowed|={'diagnostics','functional_correctness_checked','remaining_compile_calls'}
                        elif action.get('tool')=='inspect':allowed|={'case','invariant','public_action','source_sha256','remaining_inspect_calls'}
                    if set(obs)-allowed:raise ValueError('Unexpected observation fields')
                    events.append({'action_index':e['action_index'],'action':a,'omitted_action_fields':sorted(set(action)-{'tool','file','content_sha256','candidate_file'}),'executed':e['executed'],'observation':obs,'observation_delivered':e.get('observation_delivered',False)})
                p=d/'submission/bridge.sv'
                if p.exists():
                    final=artifact(p)
                    metrics=json.loads((d/'metrics.json').read_text())
                    if metrics['terminal'].get('source_sha256') not in (None,final['sha256']):raise ValueError('Terminal source mismatch')
            initial_hash=prov.get('initial_rtl_sha256')
            input_artifacts={}
            for key_name,relative in [('spec','tasks/'+task+'/spec.md'),('initial_rtl','tasks/'+task+'/workspace/bridge.sv')]:
                path=ROOT/relative;expected=m['source_files'].get(relative) if key_name=='spec' else initial_hash
                # Repair source may be published separately; never substitute the empty template.
                if key_name=='initial_rtl' and (root/'starting.sv').exists():path=root/'starting.sv'
                input_artifacts[key_name]=artifact(path) if path.exists() and sha(path)==expected else {'sha256':expected,'file':None}
            records.append({'schema':'pb-tool-trajectory-v%d'%schema_version,'episode_id':cohort+':'+name,'task_id':task,'cohort':{'study':m.get('study'),'protocol':m.get('protocol'),'repeat':row['repeat'],'model':m['model'],'policy':row['policy']},
                'versions':{'source_commit':m['source_commit'],'task_version':task_version,'verifier_manifest_sha256':verifier_hash,'policy_version':m['policies'][row['policy']]['config']['version'],'source_manifest_sha256':hashlib.sha256(canonical(m['source_files']).encode()).hexdigest(),'policy_sha256':prov['policy_sha256'],'private_reward_suite_sha256':prov.get('private_reward_suite_sha256'),'toolchain':m.get('toolchain',{})},
                'task_inputs':input_artifacts,'tool_events':events,'trajectory_available':events is not None,'final_submission':final,
                'outcome':{'reward':row['reward'],'reward_determinate':row['reward'] is not None,'valid_submission':row['valid_submission'],'category':row['terminal_category'],'infrastructure':training_infrastructure(row,feedback[name]['delivered_public_tests']),'failure_labels':row['labels']},
                'public_feedback':feedback[name]['delivered_public_tests'],
                'resources':{k:row.get(k) for k in ('tokens','wall_seconds','model_request_wall_seconds','compile_wall_seconds','simulation_wall_seconds','api_cost','actions','edits','public_test_calls','protocol_errors')},
                'optimizer_inputs_available':{'raw_model_outputs':False,'token_ids':False,'behavior_log_probabilities':False,'model_weight_revision':False}})
            if schema_version==2:
                cap=m.get('capabilities');record=records[-1]
                record['cohort']['capabilities']=cap
                names=('environment/engineering_session.py','environment/engineering_tools.py') if cap else ('environment/policy_session.py','environment/feedback.py')
                record['versions']['capability_sources']={n:m['source_files'][n] for n in names}
                extra=[e for e in events or [] if e['executed'] and e['observation_delivered'] and e['action'].get('tool') in ('compile','inspect')]
                record['engineering_feedback']=extra if events is not None else None
                record['outcome']['infrastructure']=training_infrastructure(row,feedback[name]['delivered_public_tests']+extra)
                metric_file=d/'metrics.json';metric=json.loads(metric_file.read_text()) if metric_file.exists() else {}
                for key_name in ('compile_calls','inspect_calls'):record['resources'][key_name]=metric.get(key_name)
                compiler_records=list(d.glob('compile-*/result.json'))
                record['resources']['standalone_compile_wall_seconds']=sum(json.loads(p.read_text())['wall_seconds'] for p in compiler_records) if metric.get('compile_calls')==len(compiler_records) else None
            evaluations.append({'episode_id':cohort+':'+name,'reserved_suite_sha256':prov.get('reserved_evaluation_suite_sha256'),'held_out_reward':row['held_out'],'infrastructure_error':'held_out' in row.get('environment_error_locations',[]),'use':'evaluation_only_not_training_reward'})
            offline.append({'episode_id':cohort+':'+name,'first_candidate_public':row.get('first_candidate_public'),'use':'post_hoc_measurement_not_additional_solver_observation'})
    for name,data in [('training/rollouts.jsonl',records),('evaluation/heldout.jsonl',evaluations),('analysis/offline.jsonl',offline)]:
        (out/name).write_text(''.join(json.dumps(x,sort_keys=True)+'\n' for x in data))
    manifest={'schema':'pb-exchange-manifest-v%d'%schema_version,'completed':True,'records':len(records),'available_tool_trajectories':sum(r['trajectory_available'] for r in records),'sources':source_rows,
      'scope':'All published started trials retained; selected tool trajectories and artifacts only. Not lossless model-token data or an on-policy RL training dataset. Null rewards are not relabeled. Held-out and post-hoc measurements are separate.',
      'files':{str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()}}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');return manifest
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('sources',nargs='+');p.add_argument('--schema-version',type=int,choices=(1,2),default=1);a=p.parse_args();m=export(a.sources,a.out,a.schema_version);print(json.dumps({k:v for k,v in m.items() if k not in ('files','sources')},indent=2))
