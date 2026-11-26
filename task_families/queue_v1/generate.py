"""Finite retirement-queue family. Specialization preserves historical Task003."""
import argparse,hashlib,io,json,re,shutil,subprocess,sys,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).parent
BASE='194ffbe181601e4876035a35bfa49e7242317d41';OLD='axil_to_apb4_queue_003'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def obligations(c):
 w=c['write_capacity'];r=c['read_capacity']
 return [
 {'id':'G_CAPACITY_LEVELS','contract':{'aw':w,'w':w,'ar':r},'stimulus':['family_write_laps','family_read_laps'],'oracle':'Independent pin-handshake ledger compared with scoreboard queues; capacity and available-credit latency checked','coverage':['g_%s_level_%d'%(ch,n) for ch,cap in [('aw',w),('w',w),('ar',r)] for n in range(cap+1)],'controls':['bad_over_capacity','bad_coupled_w']},
 {'id':'G_MULTIPLE_LAPS','contract':'Per-direction FIFO order across more than three capacity lengths','stimulus':['family_write_laps','family_read_laps'],'oracle':'Ordered accepted transaction identities and exact APB payloads, not candidate pointer state','coverage':['g_write_laps','g_read_laps'],'controls':['bad_wrong_address']+(['bad_wrap'] if w>1 else [])+(['bad_read_wrap'] if r>1 else [])},
 {'id':'G_RETIREMENT_BOUNDARY','contract':'Only B/R handshakes release credits; same-edge reuse optional','stimulus':['intake_b_stall','intake_r_stall','family_write_laps','family_read_laps'],'oracle':'Separate monitor ledger counts acceptance minus retirement and reset cancellation','coverage':['g_offer_at_retirement'],'controls':['bad_early_credit','bad_drops_response','bad_same_edge']}]
def ring(text,w,r):
 text=text.replace('logic [31:0] aq[0:1],dq[0:1],rq[0:1];',f'logic [31:0] aq[0:{w-1}],dq[0:{w-1}],rq[0:{r-1}];').replace('sq[0:1]',f'sq[0:{w-1}]')
 text=text.replace('logic awp,wp,rp,arp,wrp,rrp;','integer awp,wp,rp,arp,wrp,rrp;').replace('logic [1:0] ac,wc,rc;','integer ac,wc,rc;')
 for count,cap in [('ac',w),('wc',w),('rc',r)]:text=text.replace(count+'<2',count+'<'+str(cap))
 for ptr,cap in [('awp',w),('wp',w),('arp',w),('wrp',w),('rp',r),('rrp',r)]:text=text.replace('!'+ptr,'('+ptr+'=='+str(cap-1)+'?0:'+ptr+'+1)')
 return text

def generate(c,out):
 approved=json.loads((HERE/'contracts.json').read_text())['instances']
 if c not in approved:raise ValueError('Only reviewed queue contracts are supported')
 out=Path(out).resolve()
 if out.exists():raise ValueError('Never overwrite a capsule')
 data=subprocess.check_output(['git','archive',BASE],cwd=str(ROOT));out.mkdir(parents=True)
 with tarfile.open(fileobj=io.BytesIO(data)) as t:
  for m in t.getmembers():
   if m.issym() or m.islnk() or m.name.startswith('/') or '..' in Path(m.name).parts:raise ValueError('Unsafe archive')
  t.extractall(str(out))
 # Keep runtime dependencies plus exact historical baseline evidence needed by checks.
 baseline=json.loads((out/'tasks/axil_to_apb4_001/baseline.json').read_text())
 keep={Path(k).parts[1] for k in baseline['evidence_files'] if k.startswith('experiments/')}
 for p in (out/'experiments').iterdir():
  if p.name not in keep:
   if p.is_dir():shutil.rmtree(str(p))
   else:p.unlink()
 shutil.rmtree(str(out/'docs'))
 w=c['write_capacity'];r=c['read_capacity'];tid=c['task_id']
 (out/'tasks'/OLD).rename(out/'tasks'/tid)
 for directory in ('environment','scripts','tasks','tests'):
  for p in (out/directory).rglob('*'):
   if p.is_file() and p.suffix in ('.py','.json','.md'):
    t=p.read_text()
    if OLD in t:p.write_text(t.replace(OLD,tid))
 registry=json.loads((out/'tasks/registry.json').read_text());registry['tasks']=[x for x in registry['tasks'] if x['task_id']==tid];registry['tasks'][0]['title']=c['purpose'];write(out/'tasks/registry.json',registry)
 fixtures=out/'fixtures/task003';ref=ring((fixtures/'reference.sv').read_text(),w,r)
 shift=ring((fixtures/'reference_shift.sv').read_text(),w,r)
 shift=shift.replace('if(bpop) begin aq[0]<=aq[1];dq[0]<=dq[1];sq[0]<=sq[1];end',f'if(bpop) for(int i=0;i<{w-1};i++) begin aq[i]<=aq[i+1];dq[i]<=dq[i+1];sq[i]<=sq[i+1];end').replace('if(rpop) rq[0]<=rq[1];',f'if(rpop) for(int i=0;i<{r-1};i++) rq[i]<=rq[i+1];')
 for p in fixtures.glob('*.sv'):p.unlink()
 (fixtures/'reference.sv').write_text(ref);(fixtures/'reference_shift.sv').write_text(shift)
 controls=[]
 def fault(name,old,new,case,violation):
  if ref.count(old)!=1:raise ValueError('Ambiguous mutation '+name)
  (fixtures/(name+'.sv')).write_text(ref.replace(old,new));controls.append({'source':'fixtures/task003/'+name+'.sv','first_case':case,'violation':violation})
 fault('bad_over_capacity','ac<'+str(w),'ac<'+str(w+1),'family_write_laps','Accepts beyond AW unretired capacity')
 fault('bad_wrong_address','paddr<=rq[rrp]','paddr<=rq[rrp]^32\'h4','read_fifo','Corrupts accepted read address')
 fault('bad_coupled_w','rst_n && wc<'+str(w),'rst_n && ac>0 && wc<'+str(w),'partial_w','W depends on AW acceptance')
 fault('bad_blocks_reads','if(rc>0 &&','if(ac==0 && wc==0 && rc>0 &&','partial_aw','Partial write blocks eligible read')
 fault('bad_write_priority','|| prefer_read','|| 1\'b0','round_robin','Violates round-robin preference')
 fault('bad_early_credit','case({apush,bpop})','case({apush,(bpop || (state==ACCESS && pready && pwrite))})','intake_b_stall','Frees AW credit at APB completion')
 fault('bad_drops_response','RESP:if(bpop || rpop)','RESP:if(1\'b1)','intake_b_stall','Discards response under backpressure')
 fault('bad_reset_aw_credit','state<=IDLE;ac<=0;','state<=IDLE;ac<=1;','reset_1','Creates stale credit on reset')
 fault('bad_strobe_loss','pstrb<=sq[wrp]','pstrb<=4\'hf','write_fifo','Drops byte enables')
 fault('bad_error_response','s_bresp<=pslverr?2\'b10:2\'b00','s_bresp<=2\'b00','wait_error_memory','Ignores PSLVERR')
 fault('bad_ignores_wait','ACCESS:if(pready)','ACCESS:if(1\'b1)','wait_error_memory','Samples APB before ready')
 if w>1:fault('bad_wrap','awp<=(awp=='+str(w-1)+'?0:awp+1)','awp<=((awp+1)&3)','family_write_laps','Uses power-of-two wrap for capacity three')
 if r>1:fault('bad_read_wrap','rrp<=(rrp=='+str(r-1)+'?0:rrp+1)','rrp<=((rrp+1)&3)','family_read_laps','Read retirement pointer uses binary wrap for capacity three')
 (fixtures/'bad_same_edge.sv').write_text(shift.replace('aq[ac-bpop]','aq[ac]'))
 controls.append({'source':'fixtures/task003/bad_same_edge.sv','first_case':'family_write_laps','violation':'Same-edge shift and insertion use the old occupied count, losing the new AW'})
 # Scoreboard queues retain identities until response handshakes, independent of RTL arrays.
 sb=out/'verifier/task003/scoreboard.sv';t=sb.read_text();t=t.replace(' int wi=0',' int epoch_aw=0,epoch_w=0,epoch_ar=0;\n int capacity_aw=%d,capacity_w=%d,capacity_ar=%d;\n int wi=0'%(w,w,r))
 t=t.replace('aq.delete();wq.delete();rq.delete();','aq.delete();wq.delete();rq.delete();epoch_aw=0;epoch_w=0;epoch_ar=0;')
 for ch in ('aw','w','ar'):t=t.replace('accepted_'+ch+'++;','accepted_'+ch+'++;epoch_'+ch+'++;')
 for q,ch in [('aq','aw'),('wq','w'),('rq','ar')]:
  for op in ('<','>','=='):t=t.replace(q+'.size()'+op+'2',q+'.size()'+op+'capacity_'+ch)
 coverage=''
 for q,ch in [('aq','aw'),('wq','w'),('rq','ar')]:coverage+='  coverage[$sformatf("g_%s_level_%%0d",%s.size())]=1;\n'%(ch,q)
 coverage+='  if(epoch_aw>=%d && epoch_w>=%d) coverage["g_write_laps"]=1;\n'%(3*w,3*w)
 coverage+='  if(epoch_ar>=%d) coverage["g_read_laps"]=1;\n'%(3*r)
 coverage+='  if(pop_b && tb.s_awvalid && tb.s_awready) coverage["g_same_edge_aw"]=1;\n'
 coverage+='  if((pop_b && (tb.s_awvalid || tb.s_wvalid)) || (pop_r && tb.s_arvalid)) coverage["g_offer_at_retirement"]=1;\n'
 t=t.replace('  if(aq.size()>wq.size())',coverage+'  if(aq.size()>wq.size())');sb.write_text(t)
 tb=out/'verifier/task003/tb.sv';t=tb.read_text()
 for q,cap in [('aq',w),('wq',w),('rq',r)]:t=t.replace('sb.'+q+'.size()==2','sb.'+q+'.size()=='+str(cap))
 anchor=(HERE/'anchor.sv.in').read_text();a=json.loads((HERE/'anchors.json').read_text())[tid]
 anchor=anchor.replace('WRITE_VALUE',str(w)).replace('READ_VALUE',str(r)).replace('ANCHOR_W',str(a[0])).replace('ANCHOR_R',str(a[2]))
 anchor=anchor.replace('if(anchor_aw!=',f'if(sb.capacity_aw!={a[0]} || sb.capacity_w!={a[1]} || sb.capacity_ar!={a[2]}) `uvm_fatal("PB_INFRA","Capacity differs from reviewed anchor")\n  if(anchor_aw!=')
 t=t.replace(' bridge dut(.*);',anchor+'\n bridge dut(.*);').replace('sb.before_edge();#1;','family_before();sb.before_edge();family_check();#1;');tb.write_text(t)
 p=out/'verifier/task003/scenarios.py';p.rename(p.with_name('_protocol_template.py'));p.write_text((HERE/'scenarios.py.in').read_text().replace('WRITE_VALUE',str(w)).replace('READ_VALUE',str(r)))
 p=out/'verifier/task003/campaign.py';p.write_text(p.read_text().replace("if 'PB_INFRA' in log or","if 'PBQ_ANCHOR_OK' not in log or 'PB_INFRA' in log or"))
 task=out/'tasks'/tid;p=task/'spec.md';t=p.read_text().replace('task 003, revision 1',tid+' — queue family v1')
 start=t.index('- Store up to TWO');end=t.index('- AWREADY',start)
 t=t[:start]+f'''- Store up to {w} accepted AW and {w} accepted W payloads independently.
  Only a B response handshake retires one AW and W credit. Executing writes and
  pending B responses retain both credits. A partial write occupies its own half.
- Store up to {r} accepted AR payloads, retained until the R response handshake.
- Maximum complete unretired writes is {w}, reads is {r}; the directions have
  separate capacity. Reset cancels all credits. Depth one requires no rotating
  storage index; depth three must handle non-power-of-two wrap correctly.
'''+t[end:]
 t=t.replace('- Never accept a third unretired AW, W or AR.','- Never exceed the per-channel unretired capacities declared above.');p.write_text(t)
 m=json.loads((task/'task.json').read_text());m['family']={'id':'x2p_retirement_queues_v1','contract':c,'base_commit':BASE};q=m['quality'];q['negative_controls']=controls;q['required_cross_bins']=33+(w+1)*2+(r+1)+3;q['required_requirements']+= [o['id'] for o in obligations(c)];q['spec_review']['bounds']=f'{w} AW, {w} W and {r} AR unretired credits; no APB release';write(task/'task.json',m);write(task/'obligations.json',obligations(c))
 (task/'README.md').write_text('# '+tid+'\n\n'+c['purpose']+'.\n\nThe [Spec](spec.md) defines acceptance, arbitration, completion and retirement separately. [Verification obligations](obligations.json) bind contract changes to stimulus, independent checks, observed coverage and fault controls.\n\nUse the capsule scripts/tasks.py reset/test/submit/quality/rollout entry. Generation is candidate-only; actual source-bound industrial admission is required. Finite simulation is not formal completeness.\n')
 # Specialize unit expectations, retaining rather than discarding runtime tests.
 p=out/'tests/test_queue003.py';t=p.read_text().replace('len(suite(True)),19','len(suite(True)),21').replace('len(suite()),21','len(suite()),23').replace("len(x['rows']),4",f"len(x['rows']),{w+r}").replace('len(REQUIRED_BINS),33',f'len(REQUIRED_BINS),{q["required_cross_bins"]}')
 t=t.replace("log='PBQ_SEQUENCE", "log='PBQ_ANCHOR_OK\\nPBQ_SEQUENCE").replace("interpret('UVM_ERROR [PB_TIMING]", "interpret('PBQ_ANCHOR_OK\\nUVM_ERROR [PB_TIMING]");p.write_text(t)
 (out/'README.md').write_text('# Generated retirement-queue task\n\nStart with [the task](tasks/'+tid+'/README.md). This is a source-bound candidate package, not inherited admission. Historical Task001–004 contracts remain separately frozen. Inherited research utilities outside the declared CLI retain their original scope.\n')
 # V2 observation is an independently named capability, only in this new capsule.
 shutil.copyfile(str(ROOT/'environment/runtime_navigation.py'),str(out/'environment/runtime_navigation.py'))
 for name in ('environment/runtime_session.py','environment/policy_experiment.py','environment/policy_utm_agent.py','scripts/audit_policy.py','scripts/rollout_exchange_v3.py'):
  p=out/name;p.write_text(p.read_text().replace('runtime-observe-v1','runtime-events-v2'))
 p=out/'environment/runtime_session.py';t=p.read_text().replace('from environment.runtime_tools import run,observation,cases,sha,PUBLIC','from environment.runtime_tools import run,cases,sha,PUBLIC\nfrom environment.runtime_navigation import observation,valid_start')
 t=t.replace("type(action['start'])!=int or type(action['count'])!=int or not 0<=action['start']<4096", "not valid_start(action['start']) or type(action['count'])!=int")
 t=t.replace('queries the most recent laboratory run', 'queries the most recent laboratory run; start may also be an event selector such as AW:0, APB_COMPLETE:0 or B:0 (zero-based occurrence, two captured cycles of lead-in)')
 t=t.replace('First read the files and test the starting candidate before repairing it.', 'Delay semantics: start_delay is from concurrent batch launch; address_delay uses previous address handshake, except W-before-AW uses first WVALID; data_delay uses WRITE_ADDR_VALID, except W-before-AW uses previous W handshake. response_stall is from BVALID/RVALID; APB_wait counts target Access waits. They are not all relative to one global clock. Named scenarios retain their own reset conditions. Successful experiments default to the first real transaction event. First read the files and test the starting candidate before repairing it.')
 p.write_text(t)
 p=out/'environment/runtime_tools.py';t=p.read_text().replace("needle='if(sb!=null) begin sb.before_edge();#1;sb.after_edge();end'", "needle='if(sb!=null) begin family_before();sb.before_edge();family_check();#1;sb.after_edge();end'")
 t=t.replace('pb_observe(0); if(sb!=null) begin sb.before_edge();#1;pb_observe(1);sb.after_edge();end','pb_observe(0); if(sb!=null) begin family_before();sb.before_edge();family_check();#1;pb_observe(1);sb.after_edge();end');p.write_text(t)
 p=out/'scripts/audit_policy.py';t=p.read_text().replace('from environment.runtime_tools import observation','from environment.runtime_navigation import observation,valid_start').replace('from environment.runtime_tools import cases,observation,timeline','from environment.runtime_tools import cases,timeline\n                from environment.runtime_navigation import observation')
 t=t.replace("type(action['start'])==int and type(action['count'])==int and 0<=action['start']<4096", "valid_start(action['start']) and type(action['count'])==int")
 p.write_text(t)
 p=out/'environment/engineering_tools.py';p.write_text(p.read_text().replace('the two unretired credits','the Spec-defined per-channel unretired credits'))
 p=out/'environment/runtime_acceptance.py';t=p.read_text().replace('from environment.runtime_tools import run,observation,ROOT,sha','from environment.runtime_tools import run,ROOT,sha\nfrom environment.runtime_navigation import observation')
 t=t.replace("all(0<=x<=2 for row in r['timeline']['samples'] for x in row['unretired'])", "all(0<=x<=cap for row in r['timeline']['samples'] for x,cap in zip(row['unretired'],"+repr([w,w,r])+'))')
 t=t.replace("any(max(row['unretired'])>2 for row in r['timeline']['samples'])", "any(any(x>cap for x,cap in zip(row['unretired'],"+repr([w,w,r]) + ")) for row in r['timeline']['samples'])")
 t=t.replace("bad_wrong_aw_head.sv',{'scenario':'partial_aw'}", "bad_wrong_address.sv',{'scenario':'read_fifo'}")
 t=t.replace("if full:\n   r=invoke('wrong-head'", "check('success_window_has_activity',any(row['events'] for row in observation(r,True)['rows']))\n  check('event_window_retirement',any('B' in row['events'] for row in observation(r,True,'B:0')['rows']))\n  if full:\n   r=invoke('wrong-head'")
 t=t.replace("check('submit',s.handle", "check('event_query',any('B' in row['events'] for row in s.handle({'tool':'observe','start':'B:0','count':8})['rows']))\n  check('absent_event',s.handle({'tool':'observe','start':'B:99','count':8})['window']['status']=='NOT_CAPTURED')\n  check('invalid_event',s.handle({'tool':'observe','start':'private:0','count':8})['status']=='REJECTED')\n  check('fourth_query',s.handle({'tool':'observe','start':'AW:0','count':8})['window']['status']=='FOUND')\n  check('fifth_query_denied',s.handle({'tool':'observe','start':'AW:0','count':8})['reason']=='observe_budget_exhausted')\n  check('submit',s.handle")
 p.write_text(t)
 # New exchange version explicitly carries event selectors and dynamic task IDs.
 exchange=(out/'scripts/rollout_exchange_v3.py').read_text().replace("('synthesis-tools-v1','runtime-verdict-v1','runtime-events-v2')", "(None,'runtime-events-v2')").replace('v3','v4').replace('V3','V4')
 exchange=exchange.replace("'remaining_observe_calls'}", "'remaining_observe_calls','window','event_counts'}")
 (out/'scripts/rollout_exchange_v4.py').write_text(exchange)
 p=out/'environment/task_quality.py';t=p.read_text().replace('from environment.control_bank import bundle','from environment.control_bank import bundle\nfrom environment.verification_timing import measured_grade')
 t=t.replace('r=backend.grade(source,dest,public=is_public,','r=measured_grade(backend.grade,source,dest,measurement_backend=backend,public=is_public,');p.write_text(t)
 # Producer tests run at root. Capsule contains only runtime/platform tests from pinned base.
 subprocess.run([sys.executable,'-m','compileall','-q','environment','scripts','verifier','tests'],cwd=str(out),check=True)
 test=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-q'],cwd=str(out),stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 (out/'.local').mkdir(exist_ok=True);(out/'.local/generation-tests.log').write_bytes(test.stdout)
 if test.returncode:raise RuntimeError('Generated runtime tests failed; preserved candidate')
 write(out/'generation-check.json',{'passed':True,'count':int(re.search(rb'Ran (\d+) tests',test.stdout).group(1))})
 files={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and '.local' not in p.relative_to(out).parts}
 manifest={'schema':'task-capsule-v1','family':'x2p_retirement_queues_v1','task_id':tid,'source_commit':BASE,'parameters':c,'producer_files':{str(p.relative_to(ROOT)):sha(p) for p in sorted(list(HERE.glob('*'))+[ROOT/'environment/runtime_navigation.py']) if p.is_file() and p.suffix in ('.py','.json','.in')},'files':files,'status':'candidate_not_admitted'};write(out/'family-manifest.json',manifest)
 subprocess.run(['git','init','-q',str(out)],check=True);subprocess.run(['git','add','.'],cwd=str(out),check=True);subprocess.run(['git','-c','user.name=ProtocolBridge Generator','-c','user.email=generator@example.invalid','commit','-qm','Queue contract '+tid],cwd=str(out),check=True)
 return manifest
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('task');p.add_argument('out');a=p.parse_args();c=next(x for x in json.loads((HERE/'contracts.json').read_text())['instances'] if x['task_id']==a.task);m=generate(c,a.out);print(m['task_id'],len(m['files']))
