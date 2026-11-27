"""One reviewed route × retirement contract, with interaction-owned verification."""
import argparse,json,re,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from task_families.capsule import start,finish,write,BASE
HERE=Path(__file__).parent;TASK='x2p_routed_queue_v1';OLD='axil_to_apb4_queue_003'
def interface(s):
 return s.replace('output logic psel,penable,pwrite, input logic [31:0] prdata, input logic pready,pslverr','output logic [2:0] psel, input logic [95:0] prdata, input logic [2:0] pready,pslverr, output logic penable,pwrite')
def reference(s):
 s=interface(s).replace(' state_t state;',' state_t state;\n logic [1:0] target;')
 s=s.replace('assign psel=state==SETUP || state==ACCESS;','assign psel=(state==SETUP || state==ACCESS)?(3\'b001<<target):0;')
 s=s.replace('paddr<=0;','target<=0;paddr<=0;',1)
 for prefix,direction in [('rq','r'),('aq','w')]:
  pat=r'paddr<=('+prefix+r'\[\w+\]);(.*?);state<=SETUP;'
  def sub(m):
   a=m[1];body=m[2]
   return 'target<='+a+"[17:16];paddr<={16'b0,"+a+'[15:0]};'+body+';\n      if('+a+"[31:16]<3) state<=SETUP;else begin state<=RESP;"+('s_rvalid<=1;s_rresp<=3;s_rdata<=0;' if direction=='r' else 's_bvalid<=1;s_bresp<=3;')+'end'
  s,n=re.subn(pat,sub,s);assert n==1,(prefix,n)
 s=s.replace('ACCESS:if(pready)','ACCESS:if(pready[target])').replace('pslverr?','pslverr[target]?').replace('s_rdata<=prdata;','s_rdata<=prdata[32*target+:32];')
 return s

def generate(out):
 c=json.loads((HERE/'contract.json').read_text())
 if c['task_id']!=TASK or c['version']!=1 or c.get('verifier_revision')!=2 or c['capacity']!={'aw':2,'w':2,'ar':2} or c['targets']!=[[0,65536],[65536,65536],[131072,65536]]:
  raise ValueError('Only the independently reviewed composed contract is supported')
 out=start(out,OLD,TASK);v=out/'verifier/task003';f=out/'fixtures/task003';task=out/'tasks'/TASK
 refs=[reference((f/name).read_text()) for name in ('reference.sv','reference_shift.sv')]
 for p in f.glob('*.sv'):p.unlink()
 for name,text in zip(('reference.sv','reference_shift.sv'),refs):(f/name).write_text(text)
 r=refs[0];controls=[]
 def fault(name,old,new,case,why,source=None):
  text=source or r
  assert text.count(old)==1,(name,text.count(old))
  (f/(name+'.sv')).write_text(text.replace(old,new));controls.append({'source':'fixtures/task003/'+name+'.sv','first_case':case,'violation':why})
 fault('bad_over_capacity','ac<2','ac<3','write_fifo','Exceeds accepted unretired capacity')
 fault('bad_coupled_w','rst_n && wc<2','rst_n && ac>0 && wc<2','partial_w','W depends on AW')
 fault('bad_blocks_reads','if(rc>0 &&','if(ac==0 && wc==0 && rc>0 &&','partial_aw','Partial write blocks read')
 fault('bad_write_priority','|| prefer_read','|| 1\'b0','round_robin','Violates read/write preference')
 fault('bad_early_credit','case({apush,bpop})','case({apush,(bpop || (state==ACCESS && pready[target]))})','intake_b_stall','Releases AW before response retirement')
 fault('bad_drops_response','RESP:if(bpop || rpop)','RESP:if(1\'b1)','intake_b_stall','Drops stalled response')
 fault('bad_strobe','pstrb<=sq[wrp]','pstrb<=15','write_fifo','Loses byte enables')
 fault('bad_error','s_bresp<=pslverr[target]?2\'b10:2\'b00','s_bresp<=0','wait_error_memory','Drops target error')
 fault('bad_wait','ACCESS:if(pready[target])','ACCESS:if(1\'b1)','read_fifo','Uses unselected ready')
 fault('bad_target','target<=aq[arp][17:16]','target<=0','routed_identity','Queued write loses target identity')
 fault('bad_local','paddr<={16\'b0,aq[arp][15:0]}','paddr<=aq[arp]','routed_identity','Forwards global address')
 fault('bad_live_target','3\'b001<<target','3\'b001<<s_awaddr[17:16]','routed_identity','Target follows live AW instead of scheduled head')
 fault('bad_response_mux','prdata[32*target+:32]','prdata[31:0]','routed_identity','Read result comes from target zero')
 fault('bad_decerr','s_bresp<=3;','s_bresp<=0;','decerr_competition','Unmapped write is reported OKAY')
 fault('bad_decerr_ar_credit','case({rpush,rpop})','case({rpush,(rpop || (state==IDLE && rc>0 && rq[rrp][31:16]>=3))})','decerr_competition','Unmapped read releases credit on selection')
 fault('bad_decerr_preference','pwrite<=0;prefer_read<=0;','pwrite<=0;if(rq[rrp][31:16]<3) prefer_read<=0;','decerr_competition','Unmapped read does not update arbitration preference')
 fault('bad_reset_credit','state<=IDLE;ac<=0;','state<=IDLE;ac<=1;','reset_1','Reset leaves phantom AW credit')
 fault('bad_target_reset','state<=IDLE;ac<=0;','state<=IDLE;if(state==ACCESS && target==2) state<=ACCESS;ac<=0;','reset_5','Reset fails to clear Access when buffered target is two')
 fault('bad_same_edge','aq[ac-bpop]','aq[ac]','write_fifo','Simultaneous shift and insertion lose new AW',refs[1])
 # Preserve concurrent AXI sequence implementation; use three target VIP monitors.
 vip=(v/'vip.sv').read_text();router=(out/'verifier/task002/vip.sv').read_text()
 begin=vip.index('class one_request_sequence');end=vip.index('class bridge_vip_test')
 classes=router[router.index('class target_sequence'):router.index('class one_request_sequence')]
 test=router[router.index('class bridge_vip_test'):].replace('num_outstanding_xact=1','num_outstanding_xact=16').replace('address_data_sequence','queue_request_sequence').replace('PB2_DONE','PBQ_DONE')
 test=test.replace('num_outstanding_xact=16;', 'num_outstanding_xact=16;ac.master_cfg[0].reset_type=svt_axi_port_configuration::RESET_ALL_XACT;')
 test=test.replace('sb=bridge_scoreboard::type_id::create("sb",this);','sb=bridge_scoreboard::type_id::create("sb",this);tb.sb=sb;')
 header=vip[:vip.index('`include "scoreboard.sv"')]
 (v/'vip.sv').write_text(header+(HERE/'decoder.sv.in').read_text()+'\n`include "scoreboard.sv"\n'+classes+vip[begin:end]+test)
 # Queue transaction identity stays in the scoreboard; target/local mapping is independent.
 sb=(v/'scoreboard.sv').read_text();sb=sb.replace('bit prefer_read=1,in_reset=1,scheduled=0,old_psel=0;', 'bit prefer_read=1,in_reset=1,scheduled=0;bit[2:0] old_psel=0;')
 sb=sb.replace(' int wi=0',' int unmapped_completed=0,last_target=-2;bit last_unmapped=0;\n int wi=0')
 sb=sb.replace('(a^32\'h9e3779b9)','(expected_local(a)^32\'h9e3779b9^(expected_target(a)*32\'h01010101))')
 sb=sb.replace('function void write_apb(svt_apb_transaction p);','function void write_apb(svt_apb_transaction p);bad("Unexpected unindexed APB monitor");endfunction\n function void write_target(svt_apb_transaction p,int target_index);')
 sb=sb.replace('p.address!==a','p.address!==expected_local(a) || target_index!=expected_target(a)')
 sb=sb.replace('expected_error?svt_axi_transaction::SLVERR:svt_axi_transaction::OKAY','expected_target(expected.addr)<0?svt_axi_transaction::DECERR:(expected_error?svt_axi_transaction::SLVERR:svt_axi_transaction::OKAY)')
 sb=sb.replace('a.data[0][31:0]!==value_at(expected.addr)','a.data[0][31:0]!==(expected_target(expected.addr)<0?32\'b0:value_at(expected.addr))')
 sb=sb.replace('  have_axi=1;','  if(expected_target(expected.addr)<0) unmapped_completed++;\n  have_axi=1;')
 sb=sb.replace('if(active && have_apb && !have_axi)','if(active && have_apb && !have_axi && expected_target(expected.addr)>=0)')
 sb=sb.replace('reset_events++;first_after_reset=1;','reset_events++;first_after_reset=1;if(active && expected_target(expected.addr)<0) coverage["x_reset_decerr"]=1;if(active && expected_target(expected.addr)>=0) coverage[$sformatf("x_reset_mapped_%0d",expected_target(expected.addr))]=1;')
 sb=sb.replace('busy=0;active=0;have_axi=0;','last_target=-2;last_unmapped=0;busy=0;active=0;have_axi=0;')
 hook='''   if(last_unmapped && ew && er) coverage["x_after_decerr_contended"]=1;
   if(expected_target(expected.addr)>=0) begin
    coverage[$sformatf("x_target_%0d",expected_target(expected.addr))]=1;
    if(aq.size()>1 || wq.size()>1 || rq.size()>1) coverage[$sformatf("x_queued_target_%0d",expected_target(expected.addr))]=1;
    if(last_target>=0 && last_target!=expected_target(expected.addr)) coverage["x_switch"]=1;
   end else begin
    have_apb=1;apb_completed=1;response_age=0;
    coverage[expected.xact_type==svt_axi_transaction::WRITE?"x_unmapped_write":"x_unmapped_read"]=1;
   end
   last_target=expected_target(expected.addr);last_unmapped=last_target<0;
'''
 sb=sb.replace('   scheduled=1;grant_count++;',hook+'   scheduled=1;grant_count++;')
 sb=sb.replace('  if(tb.s_bvalid && tb.s_rvalid)', '  if(active && expected_target(expected.addr)<0) begin\n   if(tb.psel || tb.penable) bad("Unmapped request produced APB side effect");\n   if((tb.s_bvalid && !tb.s_bready)||(tb.s_rvalid && !tb.s_rready)) coverage["x_decerr_stall"]=1;\n  end\n  if(tb.s_bvalid && tb.s_rvalid)')
 sb=sb.replace("if(tb.psel!==1'b1 || tb.penable!==1'b0)","if(tb.psel!==(3'b001<<expected_target(expected.addr)) || tb.penable!==1'b0)")
 sb=sb.replace('if(tb.paddr!==expected.addr','if(tb.paddr!==expected_local(expected.addr)')
 sb=sb.replace('  if(scheduled) begin','  if(scheduled && expected_target(expected.addr)<0) begin\n   if(tb.psel || tb.penable || (expected.xact_type==svt_axi_transaction::WRITE?!tb.s_bvalid:!tb.s_rvalid)) timing("Registered DECERR grant missing or APB side effect");\n  end else if(scheduled) begin')
 sb=sb.replace('apb_count!=checked+aborted_apb','apb_count!=checked-unmapped_completed+aborted_apb')
 sb=sb.replace('  $display("PBQ_RESULT','  $display("PBX_UNMAPPED completed=%0d",unmapped_completed);\n  $display("PBQ_RESULT')
 (v/'scoreboard.sv').write_text(sb)
 # Multi-target electrical integration, reusing the proven queue driver/reset scheduler.
 tb=(v/'tb.sv').read_text();multi=(out/'verifier/task002/tb.sv').read_text()
 a=tb.index(' wire psel,penable,pwrite;');b=tb.index(' task wait_reset_stage',a)
 tb=tb[:a]+''' wire [2:0] psel;wire penable,pwrite;
 wire [95:0] prdata_bus;wire [2:0] pready_bus,pslverr_bus;
 wire pready=|(pready_bus & psel);
'''+tb[b:]
 a=tb.index(' bridge dut');b=tb.index(' svt_axi_if axi_if()',a);ma=multi.index(' bridge dut');mb=multi.index(' svt_axi_if axi_if()',ma);tb=tb[:a]+multi[ma:mb]+tb[b:]
 a=tb.index(' // Response values');b=tb.index(' initial begin',a);tb=tb[:a]+tb[b:]
 tb=tb.replace('vip_if.pwdata','vip_if[0].pwdata').replace('vip_if.pstrb','vip_if[0].pstrb')
 tb=tb.replace('  uvm_config_db#(svt_apb_vif)::set(null,"uvm_test_top.apb","vif",vip_if);','')
 tb=tb.replace('$stable({paddr,','$stable({psel,paddr,')
 anchor=(ROOT/'task_families/queue_v1/anchor.sv.in').read_text().replace('WRITE_VALUE','2').replace('READ_VALUE','2').replace('ANCHOR_W','2').replace('ANCHOR_R','2').replace('PBQ_LEDGER_EXECUTED','PBX_LEDGER_EXECUTED')
 anchor=anchor.replace('if(rst_n) ledger_observations++;','ledger_observations++;')
 anchor+='''\n initial begin
  if(expected_target(32'hffff)!=0 || expected_target(32'h10000)!=1 || expected_target(32'h1ffff)!=1 || expected_target(32'h20000)!=2 || expected_target(32'h2ffff)!=2 || expected_target(32'h30000)!=-1 || expected_target(32'hffffffff)!=-1 || expected_local(32'h1fffc)!=32'hfffc) $fatal(1,"PB_INFRA: independent route anchor mismatch");
  $display("PBX_ORACLE_OK");
 end
'''
 tb=tb.replace(' bridge dut',anchor+'\n bridge dut').replace('sb.before_edge();#1;','family_before();sb.before_edge();family_check();#1;')
 tb=tb.replace('endmodule',' assert property (@(posedge clk) disable iff(!rst_n) $onehot0(psel)) else `uvm_error("PB_TIMING","Multiple targets selected")\nendmodule')
 (v/'tb.sv').write_text(tb)
 (v/'scenarios.py').rename(v/'_protocol_template.py');(v/'scenarios.py').write_text((HERE/'scenarios.py.in').read_text())
 p=v/'campaign.py';s=p.read_text();s=s.replace("if 'PB_INFRA' in log or","if 'PBX_ORACLE_OK' not in log or 'PBX_LEDGER_EXECUTED' not in log or 'PB_INFRA' in log or").replace('elif rc==0 and count and credits',"elif 'PBX_LEDGER_EXECUTED' in log and rc==0 and count and credits")
 s=s.replace("c['apb']==c['checked']+c['aborted_apb']","c['apb']==c['checked']-int(re.search(r'PBX_UNMAPPED completed=(\\d+)',log).group(1))+c['aborted_apb']")
 s=s.replace("elif stage in (7,8) and c['aborted_apb']!=1:","elif stage in (7,8) and c['aborted_apb']!=(0 if case['name'].startswith('reset_decerr_') else 1):")
 # Central environment owns invocation; no per-machine environment assembly.
 s=s.replace('from .scenarios import suite,REQUIRED_BINS','from .scenarios import suite,REQUIRED_BINS\nfrom environment.remote_backend import remote_command')
 s=s.replace("return run((['/bin/bash','-lc',command] if local else ssh+[command]),timeout)","return run((['/bin/bash','-lc',remote_command(cfg,command)] if local else ssh+[remote_command(cfg,command)]),timeout)")
 s=s.replace('source ~/.bashrc; ','')
 p.write_text(s)
 p=task/'workspace/bridge.sv';p.write_text(interface(p.read_text()))
 p=task/'spec.md';s=p.read_text().replace('task 003, revision 1',TASK+' revision 1');s=s.replace('single APB4 target','three APB4 targets')
 s=s.replace('There is one APB target, no address decoding: pass all\naddress bits unchanged.', 'There are three APB targets with address decoding and local address translation\ndefined below.')
 s=s.replace('start its APB setup during the cycle', 'start its mapped APB setup (or unmapped DECERR response) during the cycle')
 s=s.replace('Each selected non-aborted request', 'Each selected mapped non-aborted request').replace('PSEL=1/PENABLE=0, then access with both high until PREADY=1.', 'exactly the selected PSEL bit high and PENABLE=0, then Access with PENABLE=1\n  until the selected PREADY bit is high.')
 s=s.replace('Only at APB completion sample PRDATA and PSLVERR.', 'For mapped requests, only at APB completion sample selected PRDATA and PSLVERR.').replace('BVALID/RVALID cannot precede the corresponding APB completion', 'For mapped requests, BVALID/RVALID cannot precede the corresponding APB completion')
 s+='''\n## Routed queue contract (normative additions)

Three independent APB4 targets share PADDR/PWDATA/PWRITE/PSTRB/PPROT/PENABLE.
PSEL is a 3-bit one-hot-or-zero vector. PREADY and PSLVERR are 3-bit input
vectors; PRDATA is 96 bits, target i in [32*i +: 32]. Only the selected target
may complete the current transfer. Unselected input values have no meaning.

Address windows (byte addresses, inclusive): target 0: 0x00000000..0x0000ffff;
target 1: 0x00010000..0x0001ffff; target 2: 0x00020000..0x0002ffff.
APB PADDR is the AXI address minus the selected window base. The same local
address on different targets identifies different storage. All other addresses
are unmapped. All accesses remain aligned 32-bit transactions with byte strobes.

A mapped FIFO head follows the original registered selection/Setup/Access rules.
Decode the scheduled buffered address, not live AXI pins. Retain target identity,
local address and payload throughout Setup and all Access waits. Capture only
that target's response and retain it under AXI response backpressure.

An unmapped head occupies the same AW/W or AR capacity and participates in the
same round-robin selection as a mapped head. At its registered selection edge,
produce BVALID/BRESP=DECERR or RVALID/RRESP=DECERR/RDATA=0 immediately after the
edge, with PSEL=0 and PENABLE=0. No APB operation occurs. Retain credits and the
executor until the B/R response handshake, update arbitration preference on
selection (including errors), and resume normal mapped work after retirement.
Reset cancels mapped and unmapped queued/executing/pending requests alike.
An unmapped request is not a bypass around older FIFO heads or arbitration.

These additions replace only the original single-target address/response mapping.
Other queue, arbitration, response-retirement and reset rules remain normative.
No multiple APB executors, response decoupling, AXI IDs/bursts or arbitrary depths.
''';p.write_text(s)
 obligations=[{'id':'X_ROUTE_QUEUE','kind':'capability_interaction','stimulus':['routed_identity'],'oracle':'Queued identity, independently decoded target and local address; selected VIP monitor and poisoned unselected response buses','coverage':['x_target_%d'%i for i in range(3)]+['x_queued_target_%d'%i for i in range(3)]+['x_switch'],'controls':['bad_target','bad_local','bad_live_target','bad_response_mux']},{'id':'X_DECERR_LIFECYCLE','kind':'capability_interaction','stimulus':['decerr_competition'],'oracle':'Virtual error grant; external handshake credit ledger; no APB side effect; FIFO and preference history','coverage':['x_unmapped_write','x_unmapped_read','x_decerr_stall','x_after_decerr_contended'],'controls':['bad_decerr','bad_decerr_ar_credit','bad_decerr_preference']},{'id':'X_RESET_DECERR','kind':'capability_interaction','stimulus':['reset_decerr_7','reset_decerr_8'],'oracle':'Canceled unretired credits and zero virtual APB completion count','coverage':['x_reset_decerr'],'controls':['bad_reset_credit']}]
 obligations.append({'id':'X_RESET_TARGET_IDENTITY','kind':'capability_interaction','stimulus':['reset_3','reset_4','reset_5','reset_6','reset_7','reset_8'],'oracle':'At active reset, independently decoded buffered target; reset quiescence and canceled-credit ledger','coverage':['x_reset_mapped_%d'%i for i in range(3)],'controls':['bad_target_reset']})
 write(task/'obligations.json',obligations)
 m=json.loads((task/'task.json').read_text());m['family']=c;m['verifier_revision']=2;m['title']='Queued multi-target AXI4-Lite to APB4';m['capabilities']+=['queued_target_identity','decerr_retirement','route_queue_interactions'];q=m['quality'];q['negative_controls']=controls;q['required_cross_bins']=48;q['required_requirements']+=['X_ROUTE_QUEUE','X_DECERR_LIFECYCLE','X_RESET_DECERR','X_RESET_TARGET_IDENTITY'];q['spec_review']['bounds']='Three 64KiB targets; two AW/W/AR unretired credits each; mapped and DECERR share retirement-coupled executor';write(task/'task.json',m)
 reg=json.loads((out/'tasks/registry.json').read_text());reg['tasks'][0]['capabilities']=m['capabilities'];reg['tasks'][0]['title']=m['title'];write(out/'tasks/registry.json',reg)
 p=out/'tests/test_queue003.py';s=p.read_text().replace('len(suite(True)),19','len(suite(True)),23').replace('len(suite()),21','len(suite()),25').replace('len(REQUIRED_BINS),33','len(REQUIRED_BINS),48');s=s.replace("log='PBQ_SEQUENCE","log='PBX_ORACLE_OK\\nPBX_LEDGER_EXECUTED\\nPBX_UNMAPPED completed=0\\nPBQ_SEQUENCE").replace("interpret('UVM_ERROR [PB_TIMING]","interpret('PBX_ORACLE_OK\\nPBX_LEDGER_EXECUTED\\nUVM_ERROR [PB_TIMING]");p.write_text(s)
 p=out/'environment/task_quality.py';s=p.read_text().replace('from environment.control_bank import bundle','from environment.control_bank import bundle\nfrom environment.verification_timing import measured_grade').replace('r=backend.grade(source,dest,public=is_public,','r=measured_grade(backend.grade,source,dest,measurement_backend=backend,public=is_public,');p.write_text(s)
 # Renamed controls must remain reachable by the real mechanism runner.
 p=out/'environment/task003_mechanism.py';p.write_text(p.read_text().replace('bad_strobe_loss.sv','bad_strobe.sv'))
 # Multi-target pin observations are not yet supported by the single-target lab.
 p=out/'environment/policy_experiment.py';s=p.read_text();s=s.replace("    if capabilities not in (", "    if capabilities is not None:raise ValueError('Composed v1 supports base observation policies only')\n    if capabilities not in (",1);p.write_text(s)
 p=out/'environment/policy_utm_agent.py';s=p.read_text().replace("    capabilities=bootstrap.get('capabilities')", "    capabilities=bootstrap.get('capabilities')\n    if capabilities is not None:raise ValueError('Composed v1 supports base observation policies only')");p.write_text(s)
 (task/'README.md').write_text('# Queued multi-target protocol conversion\n\nThe [Spec](spec.md) combines target identity and retirement-held queues. [Interaction obligations](obligations.json) bind actual behavior to independent checks, coverage and controls. Use scripts/tasks.py reset/test/submit/quality/rollout; only source/toolchain-matched industrial admission permits rollout. Generation alone is not admission.\n')
 (out/'README.md').write_text('# Composed contract capsule\n\nSee [task](tasks/'+TASK+'/README.md). Candidate source, not inherited industrial admission.\n')
 return finish(out,TASK,c['family'],c,[ROOT/'task_families/capsule.py']+[p for p in HERE.iterdir() if p.is_file() and p.suffix in ('.py','.json','.in')])
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('out');a=p.parse_args();print(generate(a.out)['task_id'])
