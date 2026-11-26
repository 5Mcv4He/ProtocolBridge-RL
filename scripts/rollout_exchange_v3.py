"""Audited raw-episode to reviewed tool exchange. Held-out evidence stays separate.
V3 adds source-bound synthesis and structured runtime laboratory observations.
It does not export raw SDK responses, private vectors, or implementation reports.
"""
import hashlib,json
from pathlib import Path
from scripts.audit_policy import audit
from scripts.batch_analysis import report

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def export(sources,out):
 roots=[Path(p).resolve() for p in sources]
 if len(set(roots))!=len(roots):raise ValueError('Duplicate source')
 prepared=[]
 for root in roots:
  checked=audit(root)
  if not checked['accepted']:raise ValueError('Raw episode audit failed')
  manifest=json.loads((root/'experiment.json').read_text())
  if manifest.get('capabilities') not in ('synthesis-tools-v1','runtime-verdict-v1','runtime-observe-v1'):raise ValueError('Unsupported v3 capability')
  analysis=report(root,len(manifest['schedule']))
  if len(analysis['rows'])!=len(manifest['schedule']):raise ValueError('Incomplete cohort; preserve it before exporting')
  prepared.append((root,manifest,analysis))
 out=Path(out);out.mkdir(parents=True,exist_ok=False)
 for name in ('training','evaluation','analysis','artifacts'):(out/name).mkdir()
 records=[];evaluations=[];offline=[]
 def artifact(data,suffix):
  digest=hashlib.sha256(data).hexdigest();name='artifacts/'+digest+suffix
  (out/name).write_bytes(data);return {'sha256':digest,'file':name}
 for root,m,a in prepared:
  cohort=sha(root/'experiment.json');cap=m['capabilities']
  for row in a['rows']:
   d=root/row['trial'];metrics=json.loads((d/'metrics.json').read_text());trace=json.loads((d/'trace.json').read_text());events=[]
   for event in trace:
    action=dict(event['action']);obs=dict(event['observation']);tool=action.get('tool')
    if 'content' in action:
     value=action.pop('content')
     if not isinstance(value,str):raise ValueError('Non-text edit cannot be represented by this exporter')
     action['content_artifact']=artifact(value.encode(),'.sv')
    allowed={'status','reason','instruction','action_fields','file','content','remaining_test_calls','category','first_failed_case','diagnostic'}
    if tool=='synth_check':allowed|={'diagnostics','functional_correctness_checked','remaining_synth_calls'}
    if tool in ('experiment','observe'):allowed|={'source_sha256','invariant','signals','rows','first_error','capture_limit_cycles','truncated','remaining_experiment_calls','experiment_action','remaining_observe_calls'}
    if set(obs)-allowed:raise ValueError('Unauthorized observation field')
    if 'content' in obs:obs['content_artifact']=artifact(obs.pop('content').encode(),'.txt')
    events.append({'action_index':event['action_index'],'action':action,'executed':event['executed'],
                   'observation':obs,'observation_delivered':event.get('observation_delivered',False)})
   final=artifact((d/'submission/bridge.sv').read_bytes(),'.sv') if metrics['submitted'] else None
   key=cohort+':'+row['trial']
   public_errors=any(e['executed'] and e['observation_delivered'] and e['observation'].get('status')=='ENV_ERROR' for e in events)
   records.append({'schema':'pb-tool-trajectory-v3','episode_id':key,'task_id':m['task_id'],
     'cohort':{'model':m['model'],'protocol':m['protocol'],'capabilities':cap,'policy':row['policy'],'study':m['study']},
     'versions':{'source_commit':m['source_commit'],'source_files':m['source_files'],'policy_sha256':metrics['policy_sha256'],
                 'private_reward_suite_sha256':metrics['private_reward_suite_sha256'],'toolchain':m['toolchain']},
     'initial_prompt':artifact((d/'initial-prompt.txt').read_bytes(),'.txt'),
     'tool_events':events,'final_submission':final,
     'outcome':{'reward':row['reward'],'valid_submission':row['valid_submission'],'category':row['terminal_category'],
                'infrastructure':row['terminal_category']=='infrastructure_error' or public_errors},
     'resources':{k:row.get(k) for k in ('tokens','wall_seconds','model_request_wall_seconds','compile_wall_seconds','simulation_wall_seconds','api_cost','actions','edits','public_test_calls','protocol_errors')},
     'tool_counts':{k:metrics.get(k,0) for k in ('synth_calls','experiment_calls','observe_calls')},
     'tool_wall_seconds':{name:sum(json.loads(p.read_text()).get('wall_seconds',0) for p in d.glob(pattern)) for name,pattern in [('synthesis','synth-*/result.json'),('laboratory','experiment-*/result.json')]},
     'optimizer_inputs_available':{'token_ids':False,'behavior_log_probabilities':False,'model_weight_revision':False}})
   evaluations.append({'episode_id':key,'held_out_reward':row['held_out'],'suite_sha256':metrics['reserved_evaluation_suite_sha256'],'use':'evaluation_only_not_training_reward'})
   offline.append({'episode_id':key,'first_candidate_public':row.get('first_candidate_public'),'use':'post_hoc_not_solver_feedback'})
 for name,value in [('training/rollouts.jsonl',records),('evaluation/heldout.jsonl',evaluations),('analysis/offline.jsonl',offline)]:
  (out/name).write_text(''.join(json.dumps(v,sort_keys=True)+'\n' for v in value))
 result={'schema':'pb-exchange-manifest-v3','exporter_sha256':sha(__file__),'completed':True,'records':len(records),'available_tool_trajectories':len(records),
         'source_experiment_sha256':[sha(root/'experiment.json') for root in roots],
         'scope':'Audit-required complete raw cohorts. Tool feedback only; no private vectors, raw SDK reasoning, netlists or trusted implementation results. Not lossless on-policy training data.',
         'files':{str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()}}
 (out/'manifest.json').write_text(json.dumps(result,indent=2)+'\n');return result
