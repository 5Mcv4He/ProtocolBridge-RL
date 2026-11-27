"""Summarize audited artifacts without relabeling offline results as feedback."""
import argparse,json,re
from pathlib import Path
from scripts.artifact_exchange import audit
from environment.artifact_task.session import sha,save

def summarize(roots):
 rows=[]
 for root in map(Path,roots):
  a=audit(root);r=json.loads((root/'result.json').read_text());plan=json.loads((root/'freeze.json').read_text());trace=json.loads((root/'session/trace.json').read_text())
  edits=[e for e in trace if e['executed'] and e['action'].get('tool')=='edit'];tests=[e for e in trace if e['executed'] and e['action'].get('tool')=='test']
  first=edits[0]['observation']['source_sha256'] if edits else None
  tested_first=[e['observation']['status'] for e in tests if e['observation'].get('source_sha256')==first]
  final=r['terminal'].get('source_sha256');final_tests=[e['observation']['status'] for e in tests if e['observation'].get('source_sha256')==final]
  failed=[e['action_index'] for e in tests if e['observation_delivered'] and e['observation']['status']=='FAIL']
  after_failure=any(e['action_index']>f for e in edits for f in failed)
  compiles=list(root.rglob('compile.log'));simulation=list(root.rglob('simulation.log'));compile_cpu=[];sim_cpu=[]
  for files,target in ((compiles,compile_cpu),(simulation,sim_cpu)):
   for p in files:
    matches=re.findall(r'CPU [Tt]ime:\s*([0-9.]+) seconds',p.read_text(errors='replace'))
    if matches:target.append(float(matches[-1]))
  raw={str(p.relative_to(root)):sha(p) for p in sorted(root.rglob('*')) if p.is_file() and p.name!='raw-manifest.json'}
  save(root/'raw-manifest.json',{'files':raw})
  rows.append({'trial_id':r['trial_id'],'task_id':r['task_id'],'study':plan['study_id'],'source_plan_sha256':r['plan_sha256'],'reward':r['terminal']['reward'],'category':r['terminal']['category'],'submitted':r['submitted'],'reserved_reward':r['reserved_evaluation']['reward'] if r['reserved_evaluation'] else None,'reserved_evaluation_performed':r['reserved_evaluation'] is not None,'actions':r['actions'],'edits':r['edits'],'public_tests':r['public_test_calls'],'first_edit_public_status':tested_first[-1] if tested_first else None,'final_public_status':final_tests[-1] if final_tests else 'UNTESTED','edits_after_delivered_functional_fail':after_failure,'public_failure_feedbacks':len(failed),'protocol_errors':a['protocol_errors'],'reply_parse_errors':a['reply_parse_errors'],'action_schema_errors':a['action_schema_errors'],'tokens':a['tokens'],'model_request_seconds':r['model_request_seconds'],'public_tool_seconds':a['public_check_wall_seconds'],'terminal_seconds':r['terminal'].get('wall_seconds'),'reserved_seconds':r['reserved_evaluation'].get('wall_seconds') if r['reserved_evaluation'] else None,'whole_trial_seconds':r['wall_seconds'],'vcs_compilation_count':len(compiles),'vcs_compile_cpu_seconds':sum(compile_cpu) if compile_cpu else None,'vcs_simulation_count':len(simulation),'vcs_simulation_cpu_seconds':sum(sim_cpu) if sim_cpu else None,'api_currency_cost':None,'audited':True,'raw_manifest_sha256':sha(root/'raw-manifest.json'),'verifier_status':'superseded_known_uart_busy_offer_gap' if r['trial_id'] in ('uart-8n1-r1','uart-8e1-r1') else 'superseded_known_uart_interface_gap' if r['trial_id'] in ('uart-8n1-verifier2-r1','uart-8e1-verifier2-r1') else 'current_for_reported_contract'})
 return {'schema':'engineering-artifact-study-analysis-v1','started_trials':len(rows),'audited_trials':len(rows),'rows':rows,'totals':{'tokens':sum(x['tokens'] for x in rows),'model_request_seconds':sum(x['model_request_seconds'] for x in rows),'whole_trial_seconds':sum(x['whole_trial_seconds'] for x in rows),'actions':sum(x['actions'] for x in rows),'protocol_errors':sum(x['protocol_errors'] for x in rows)},'limits':['Different tasks, feedback versions and verifier versions are not pooled into a success-rate claim.','First-edit status comes only from tests actually requested in the episode.','Raw replies and logs remain private; selected tool observations are exported separately.','Model request wall time includes API and worker overhead. VCS CPU timings are reported only when parsable; missing costs are not invented.','Old UART verifier1/2 rewards remain historical, not current admission evidence. Held-out results never select training records.']}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('out');p.add_argument('sources',nargs='+');a=p.parse_args();r=summarize(a.sources);save(Path(a.out),r);print(json.dumps(r['totals']))
