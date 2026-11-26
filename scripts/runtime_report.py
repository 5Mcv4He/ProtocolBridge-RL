"""Describe actual laboratory exposure and subsequent edits, without causal claims."""
import argparse,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.audit_policy import audit
from scripts.batch_analysis import report as batch_report

def report(roots):
 cohorts=[]
 for root in map(Path,roots):
  m=json.loads((root/'experiment.json').read_text());checked=audit(root)
  if not checked['accepted']:raise ValueError('Audit failed')
  if m.get('capabilities') not in ('runtime-verdict-v1','runtime-observe-v1'):raise ValueError('Unexpected profile')
  a=batch_report(root,len(m['schedule']));rows=[]
  for row in a['rows']:
   trial=root/row['trial'];trace=json.loads((trial/'trace.json').read_text());metrics=json.loads((trial/'metrics.json').read_text())
   tool_events=[]
   for event in trace:
    tool=event['action'].get('tool')
    if tool not in ('experiment','observe'):continue
    tool_events.append({'action_index':event['action_index'],'tool':tool,'executed':event['executed'],
       'delivered':event.get('observation_delivered',False),'observation':event['observation'],
       'scenario':event['action'].get('scenario'),'custom_transaction_count':len(event['action'].get('transactions',[])),
       'later_edits':sum(e['executed'] and e['action'].get('tool')=='edit' and e['action_index']>event['action_index'] for e in trace) if event.get('observation_delivered') else 0})
   keys=('trial','reward','held_out','valid_submission','effective_edit','actions','edits','protocol_errors','public_test_calls',
         'terminal_category','primary_outcome','labels','tokens','wall_seconds','model_request_wall_seconds','compile_wall_seconds',
         'simulation_wall_seconds','first_candidate_public','final_candidate_public','infrastructure','case_counts','compilation_processes','simulation_processes')
   result={k:row.get(k) for k in keys}
   result.update(experiment_calls=metrics.get('experiment_calls',0),observe_calls=metrics.get('observe_calls',0),
                 laboratory_wall_seconds=sum(json.loads(p.read_text()).get('wall_seconds',0) for p in trial.glob('experiment-*/result.json')),
                 tool_events=tool_events,laboratory_environment_errors=sum(e['executed'] and e['observation'].get('status')=='ENV_ERROR' for e in tool_events if e['tool']=='experiment'),final_source_sha256=metrics['terminal'].get('source_sha256'),
                 solver_stopped_before_evaluation=metrics['solver_stopped_before_evaluation'])
   rows.append(result)
  cohorts.append({'capabilities':m['capabilities'],'model':m['model'],'protocol':m['protocol'],'source_commit':m['source_commit'],
                  'experiment_sha256':hashlib.sha256((root/'experiment.json').read_bytes()).hexdigest(),'sampling':m['sampling'],
                  'starting_rtl_sha256':m['starting_rtl_sha256'],'suite_hashes':m['paired_suite_hashes'],'toolchain':m['toolchain'],
                  'audit_accepted':checked['accepted'],'quality_gate':a['quality_gate'],'groups':a['groups'],'rows':rows})
 if cohorts:
  for key in ('model','protocol','source_commit','starting_rtl_sha256','suite_hashes','toolchain'):
   if any(c[key]!=cohorts[0][key] for c in cohorts):raise ValueError('Unmatched comparison: '+key)
 return {'schema':'runtime-study-summary-v1','analysis_code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
         'parameter_training':False,'cohorts':cohorts,'limits':['Small exploratory samples; no causal estimate or task difficulty calibration.',
         'An edit after feedback establishes order, not correct diagnosis or semantic use.','Sampled interface events are not arbitrary DUT internal waveforms.']}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('roots',nargs='+');p.add_argument('--out',required=True);a=p.parse_args()
 with Path(a.out).open('x') as f:f.write(json.dumps(report(a.roots),indent=2)+'\n')
