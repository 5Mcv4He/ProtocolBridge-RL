"""Audit a paired capability study and retain actual tool exposure, not availability proxies."""
import argparse,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.audit_policy import audit
from scripts.analyze_policy import usage
from scripts.batch_analysis import interval
from collections import Counter

def build(baseline,tools):
 roots=[Path(baseline),Path(tools)];manifests=[json.loads((p/'experiment.json').read_text()) for p in roots]
 a,b=manifests
 common=['task_id','source_commit','source_files','model','toolchain','protocol','starting_rtl_sha256','paired_suite_hashes','schedule']
 errors=[k+' differs' for k in common if a[k]!=b[k]]
 if a.get('capabilities') is not None or b.get('capabilities')!='engineering-tools-v1':errors.append('Wrong capability contrast')
 rows=[];audits=[]
 for group,root,m in zip(('baseline','engineering'),roots,manifests):
  try:audited=audit(root)
  except Exception as e:audited={'accepted':False,'errors':['Incomplete audit: '+type(e).__name__]}
  audits.append(audited)
  if not audited['accepted']:errors.extend(audited['errors'])
  for plan in m['schedule']:
   d=root/plan['id']
   if not (d/'metrics.json').exists():
    errors.append(group+'/'+plan['id']+': missing complete trial')
    if (root/(plan['id']+'-job.json')).exists() or d.exists():rows.append({'group':group,'trial':plan['id'],'repeat':plan['repeat'],'submitted':False,'reward':None,'category':'infrastructure_error','incomplete':True})
    continue
   r=json.loads((d/'metrics.json').read_text());events=json.loads((d/'trace.json').read_text())
   exposure=[{'action':e['action_index'],'tool':e['action'].get('tool'),'observation':e['observation']} for e in events if e['executed'] and e.get('observation_delivered') and e['action'].get('tool') in ('test','compile','inspect')]
   edits=[e['action_index'] for e in events if e['executed'] and e['action'].get('tool')=='edit']
   protocol_errors=sum(e['observation'].get('reason') in ('invalid_action','invalid_action_format') for e in events)
   u=usage(d.glob('harness-*.json'));timings=[x for p in d.rglob('timing.json') for x in json.loads(p.read_text())]
   compile_cost=sum(json.loads(p.read_text()).get('wall_seconds',0) for p in d.glob('compile-*/result.json'))
   rows.append({'group':group,'trial':plan['id'],'repeat':plan['repeat'],'submitted':r['submitted'],
    'reward':r['terminal']['reward'],'category':r['terminal']['category'],'held_out':r['held_out'],
    'first_candidate_public':r['first_candidate_public'],'actions':r['actions'],'edits':r['edits'],
    'public_test_calls':r['public_test_calls'],'compile_calls':r.get('compile_calls',0),'inspect_calls':r.get('inspect_calls',0),
    'protocol_errors':protocol_errors,'tool_exposure':exposure,
    'edits_after_invariant':sum(any(e['tool']=='inspect' and e['observation'].get('invariant') and e['action']<i for e in exposure) for i in edits),
    'tokens':u['totals']['totalTokens'] if u['available'] else None,'episode_seconds':r['wall_seconds'],
    'standalone_compile_seconds':compile_cost,'eda_seconds':{k:sum(x['wall_seconds'] for x in timings if x['kind']==k) for k in ('compile','simulate')},
    'trace_sha256':hashlib.sha256((d/'trace.json').read_bytes()).hexdigest()})
 groups={}
 for group in ('baseline','engineering'):
  rr=[r for r in rows if r['group']==group];n=len(rr);k=sum(r['reward']==1 for r in rr)
  groups[group]={'started':n,'valid_submissions':sum(r['submitted'] for r in rr),'successes':k,'wilson95':interval(k,n),'rewards':dict(Counter(str(r['reward']) for r in rr)),
   'tokens':sum(r.get('tokens') or 0 for r in rr) if all(r.get('tokens') is not None for r in rr) else None,
   'invariant_exposed_trials':sum(any(e['tool']=='inspect' and e['observation'].get('invariant') for e in r.get('tool_exposure',[])) for r in rr)}
 return {'schema_version':1,'groups':groups,'accepted':not errors,'errors':errors,'matched_variables':common,'rows':rows,
         'contrast':'Availability of bounded compiler and fixed public invariant queries; same diagnostic policy, task, starting RTL, 20 actions, two full public tests and paired final inputs.',
         'limits':['Small exploratory sample; no causal ranking or saturation conclusion.','Tool availability is not actual exposure; inspect must be called and delivered.','Two capabilities are added together; this is not a per-tool causal ablation.','Post-feedback edits do not establish semantic repair; inspect RTL and final verification.','API currency cost unavailable.']}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('baseline');p.add_argument('tools');p.add_argument('out');a=p.parse_args()
 out=Path(a.out)
 if out.exists():raise ValueError('Preserve existing report')
 r=build(a.baseline,a.tools);out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'accepted':r['accepted'],'trials':len(r['rows']),'errors':r['errors']}));raise SystemExit(0 if r['accepted'] else 1)
