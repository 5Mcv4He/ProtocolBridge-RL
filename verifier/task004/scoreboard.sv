// Pin transaction model plus independently consumed VIP transaction streams.
// Request queues, unretired credits, and completed responses are separate ledgers.
class response_record;
 svt_axi_transaction request;
 bit err;bit[31:0] data;
endclass
class bridge_scoreboard extends uvm_scoreboard;
 `uvm_component_utils(bridge_scoreboard)
 uvm_analysis_imp_axi#(svt_axi_transaction,bridge_scoreboard) axi_in;
 uvm_analysis_imp_apb#(svt_apb_transaction,bridge_scoreboard) apb_in;
 svt_axi_transaction wplans[int],rplans[int],expected;
 int wwait[int],rwait[int];bit werror[int],rerror[int];
 int aq[$],wq[$],rq[$];
 response_record bqueue[$],rqueue[$],apbmon[$],bmon[$],rmon[$];
 int wi=0,ri=0,wa=0,wd=0,ra=0,ac=0,wc=0,rc=0;
 int planned=0,checked=0,aborted=0,aborted_apb=0,axi_count=0,apb_count=0,errors=0;
 int accepted_aw=0,accepted_w=0,accepted_ar=0,retired_w=0,retired_r=0;
 int canceled_aw=0,canceled_w=0,canceled_ar=0,reset_events=0,grant_count=0;
 int aw_age=0,w_age=0,ar_age=0,b_age=0,r_age=0;
 bit busy=0,expected_error=0,prefer_read=1,in_reset=1,scheduled=0,old_psel=0;
 bit[31:0] mem[bit[31:0]];bit coverage[string];
 function new(string name,uvm_component parent);
  super.new(name,parent);axi_in=new("axi_in",this);apb_in=new("apb_in",this);
 endfunction
 function void bad(string why);errors++;$display("PBQ_ERROR %s",why);`uvm_error("PB_FUNCTION",why) endfunction
 function void timing(string why);errors++;$display("PBQ_ERROR %s",why);`uvm_error("PB_TIMING",why) endfunction
 function bit[31:0] value_at(bit[31:0] a);return mem.exists(a)?mem[a]:(a^32'h9e3779b9);endfunction
 function void issue(svt_axi_transaction t,bit err,int waits);
  svt_axi_transaction copy;$cast(copy,t.clone());planned++;
  if(t.xact_type==svt_axi_transaction::WRITE) begin wplans[wi]=copy;wwait[wi]=waits;werror[wi]=err;wi++;end
  else begin rplans[ri]=copy;rwait[ri]=waits;rerror[ri]=err;ri++;end
 endfunction
 function void write_apb(svt_apb_transaction p);
  response_record rec;bit wr;
  if(!tb.rst_n)return;
  apb_count++;
  if(apbmon.size()==0) begin bad("Unexpected APB monitor completion");return;end
  rec=apbmon.pop_front();wr=rec.request.xact_type==svt_axi_transaction::WRITE;
  if(p.address!==rec.request.addr || (p.xact_type==svt_apb_transaction::WRITE)!=wr) bad("APB monitor address/direction mismatch");
  if(p.pslverr_enable!=rec.err)bad("APB monitor error mismatch");
  if(wr) begin
   if(p.data[31:0]!==rec.request.data[0][31:0] || p.pstrb[3:0]!==rec.request.wstrb[0][3:0])bad("APB monitor write payload mismatch");
  end else if(p.data[31:0]!==rec.data)bad("APB monitor read snapshot mismatch");
 endfunction
 function void write_axi(svt_axi_transaction a);
  response_record rec;bit wr;
  if(!tb.rst_n)return;
  axi_count++;wr=a.xact_type==svt_axi_transaction::WRITE;
  if((wr && bmon.size()==0) || (!wr && rmon.size()==0))begin bad("Unexpected AXI monitor completion");return;end
  if(wr) rec=bmon.pop_front();else rec=rmon.pop_front();
  if(a.addr!==rec.request.addr || a.xact_type!=rec.request.xact_type)bad("AXI response pairing/order mismatch");
  if(wr) begin
   if(a.data[0]!==rec.request.data[0] || a.wstrb[0]!==rec.request.wstrb[0])bad("AXI write payload mismatch");
   if(a.bresp!=(rec.err?svt_axi_transaction::SLVERR:svt_axi_transaction::OKAY))bad("BRESP mismatch");
  end else begin
   if(a.data[0][31:0]!==rec.data)bad("Queued RDATA snapshot mismatch");
   if(a.rresp[0]!=(rec.err?svt_axi_transaction::SLVERR:svt_axi_transaction::OKAY))bad("RRESP mismatch");
  end
 endfunction
 function void before_edge();
  int id,discarded;bit ew,er,pop_b,pop_r;response_record rec;
  bit[31:0] a,mask,old;
  scheduled=0;old_psel=tb.psel;
  if(!tb.rst_n)begin
   if(!in_reset)begin
    reset_events++;discarded=planned-checked-aborted;
    if(discarded<1)`uvm_fatal("PB_INFRA","Reset interrupted no requests")
    aborted+=discarded;aborted_apb+=bqueue.size()+rqueue.size();
    canceled_aw+=ac;canceled_w+=wc;canceled_ar+=rc;
    $display("PBQ_RESET stage=%0d canceled=%0d aw=%0d w=%0d ar=%0d apb_completed=%0d",tb.reset_stage_active,discarded,ac,wc,rc,bqueue.size()+rqueue.size());
    if(ac+rc>1 || wc+rc>1)coverage["reset_queued"]=1;
    if(bqueue.size()+rqueue.size()>1)coverage["reset_completed_queue"]=1;
   end
   aq.delete();wq.delete();rq.delete();bqueue.delete();rqueue.delete();apbmon.delete();bmon.delete();rmon.delete();
   wa=wi;wd=wi;ra=ri;ac=0;wc=0;rc=0;busy=0;prefer_read=1;aw_age=0;w_age=0;ar_age=0;b_age=0;r_age=0;in_reset=1;return;
  end
  in_reset=0;ew=aq.size()>0 && wq.size()>0;er=rq.size()>0;
  if(!busy && (ew || er))begin
   if(ew && er)coverage["both_eligible"]=1;
   if(er && (!ew || prefer_read))begin
    id=rq.pop_front();$cast(expected,rplans[id].clone());expected_error=rerror[id];tb.target_wait=rwait[id];prefer_read=0;
    if((aq.size()>0)!=(wq.size()>0))coverage["read_during_partial_write"]=1;
   end else begin
    id=aq.pop_front();if(id!=wq.pop_front())bad("AW/W FIFO pairing mismatch");
    $cast(expected,wplans[id].clone());expected_error=werror[id];tb.target_wait=wwait[id];prefer_read=1;
   end
   if(tb.s_bvalid && !tb.s_bready)coverage["execute_during_b_stall"]=1;
   if(tb.s_rvalid && !tb.s_rready)coverage["execute_during_r_stall"]=1;
   tb.target_error=expected_error;busy=1;scheduled=1;grant_count++;
  end
  // Validate response heads BEFORE accepting this edge's new APB completion.
  if(tb.s_bvalid)begin
   if(bqueue.size()==0)timing("B response precedes APB completion");
   else if(tb.s_bresp!==(bqueue[0].err?2'b10:2'b00))bad("B head error mismatch");
  end
  if(tb.s_rvalid)begin
   if(rqueue.size()==0)timing("R response precedes APB completion");
   else begin
    if(tb.s_rresp!==(rqueue[0].err?2'b10:2'b00))bad("R head error mismatch");
    if(value_at(rqueue[0].request.addr)!==rqueue[0].data)coverage["read_snapshot_changed"]=1;
    if(tb.s_rdata!==rqueue[0].data)bad("R head snapshot/order mismatch");
   end
  end
  b_age=(bqueue.size()>0 && !tb.s_bvalid)?b_age+1:0;
  r_age=(rqueue.size()>0 && !tb.s_rvalid)?r_age+1:0;
  if(b_age>16 || r_age>16)timing("Completed head response latency exceeded");
  aw_age=(tb.s_awvalid && !tb.s_awready && ac<3)?aw_age+1:0;
  w_age=(tb.s_wvalid && !tb.s_wready && wc<3)?w_age+1:0;
  ar_age=(tb.s_arvalid && !tb.s_arready && rc<3)?ar_age+1:0;
  if(aw_age>16 || w_age>16 || ar_age>16)timing("Available credit acceptance latency exceeded");
  pop_b=tb.s_bvalid && tb.s_bready;pop_r=tb.s_rvalid && tb.s_rready;
  if(pop_b && bqueue.size()>0)begin rec=bqueue.pop_front();bmon.push_back(rec);ac--;wc--;retired_w++;checked++;end
  if(pop_r && rqueue.size()>0)begin rec=rqueue.pop_front();rmon.push_back(rec);rc--;retired_r++;checked++;end
  if(pop_b && pop_r)coverage["simultaneous_responses"]=1;
  if(tb.psel && tb.penable && tb.pready)begin
   if(!busy || scheduled)bad("Unexpected APB pin completion");
   rec=new();$cast(rec.request,expected.clone());rec.err=expected_error;
   a=expected.addr;old=value_at(a);rec.data=old;
   if(tb.paddr!==a || tb.pwrite!==(expected.xact_type==svt_axi_transaction::WRITE))bad("APB completion request mismatch");
   if(tb.pslverr!==expected_error)bad("APB pin error mismatch");
   if(expected.xact_type==svt_axi_transaction::WRITE)begin
    if(tb.pwdata!==expected.data[0][31:0] || tb.pstrb!==expected.wstrb[0][3:0])bad("APB completion payload mismatch");
    mask=0;for(int k=0;k<4;k++)if(expected.wstrb[0][k])mask[8*k+:8]=8'hff;
    if(!expected_error)mem[a]=(old&~mask)|(expected.data[0][31:0]&mask);
    bqueue.push_back(rec);coverage[$sformatf("strobe_%0d",expected.wstrb[0][3:0])]=1;
    if(expected_error)coverage["write_error"]=1;
    if(pop_b)coverage["b_enqueue_dequeue"]=1;
   end else begin
    if(tb.prdata!==old)bad("APB read memory mismatch");rqueue.push_back(rec);
    if(expected_error)coverage["read_error"]=1;
    if(pop_r)coverage["r_enqueue_dequeue"]=1;
   end
   apbmon.push_back(rec);busy=0;
  end
  if(tb.s_awvalid && tb.s_awready)begin
   if(!wplans.exists(wa) || tb.s_awaddr!==wplans[wa].addr)`uvm_fatal("PB_INFRA","AW source mismatch")
   aq.push_back(wa);wa++;ac++;accepted_aw++;
  end
  if(tb.s_wvalid && tb.s_wready)begin
   if(!wplans.exists(wd) || tb.s_wdata!==wplans[wd].data[0][31:0] || tb.s_wstrb!==wplans[wd].wstrb[0][3:0])`uvm_fatal("PB_INFRA","W source mismatch")
   wq.push_back(wd);wd++;wc++;accepted_w++;
  end
  if(tb.s_arvalid && tb.s_arready)begin
   if(!rplans.exists(ra) || tb.s_araddr!==rplans[ra].addr)`uvm_fatal("PB_INFRA","AR source mismatch")
   rq.push_back(ra);ra++;rc++;accepted_ar++;
  end
  if(ac>3 || wc>3 || rc>3 || ac<0 || wc<0 || rc<0)timing("Unretired capacity ledger out of bounds");
  if(ac==3)coverage["aw_full"]=1;if(wc==3)coverage["w_full"]=1;if(rc==3)coverage["ar_full"]=1;
  if(bqueue.size()==3)coverage["b_response_full"]=1;if(rqueue.size()==3)coverage["r_response_full"]=1;
  if(aq.size()>wq.size())coverage["aw_ahead"]=1;if(wq.size()>aq.size())coverage["w_ahead"]=1;
  if(tb.psel && tb.penable && !tb.pready)coverage["apb_wait"]=1;
  if(accepted_aw>9 && accepted_ar>9)coverage["long_stream"]=1;
 endfunction
 function void after_edge();
  if(!tb.rst_n)return;
  if(scheduled)begin
   if(tb.psel!==1'b1 || tb.penable!==1'b0)timing("Independent executor grant missing");
   if(tb.paddr!==expected.addr || tb.pwrite!==(expected.xact_type==svt_axi_transaction::WRITE))bad("FIFO arbitration/setup mismatch");
   if(expected.xact_type==svt_axi_transaction::WRITE && (tb.pwdata!==expected.data[0][31:0] || tb.pstrb!==expected.wstrb[0][3:0]))bad("Setup payload mismatch");
  end else if(!old_psel && tb.psel)bad("Unscheduled APB setup");
 endfunction
 function void report_phase(uvm_phase phase);
  if(planned!=tb.expected_planned)`uvm_fatal("PB_INFRA","Issued count differs from scenario")
  if(planned==0 || busy || ac || wc || rc || aq.size() || wq.size() || rq.size() || bqueue.size() || rqueue.size() || apbmon.size() || bmon.size() || rmon.size())bad("Unaccounted transactions");
  if(planned!=checked+aborted || axi_count!=checked || apb_count!=checked+aborted_apb)bad("Completion conservation mismatch");
  if(accepted_aw!=retired_w+canceled_aw || accepted_w!=retired_w+canceled_w || accepted_ar!=retired_r+canceled_ar)bad("Credit conservation mismatch");
  $display("PBQ_RESULT planned=%0d axi=%0d apb=%0d checked=%0d aborted=%0d aborted_apb=%0d errors=%0d",planned,axi_count,apb_count,checked,aborted,aborted_apb,errors);
  $display("PBQ_CREDITS aw=%0d w=%0d ar=%0d retired_w=%0d retired_r=%0d canceled_aw=%0d canceled_w=%0d canceled_ar=%0d resets=%0d grants=%0d",accepted_aw,accepted_w,accepted_ar,retired_w,retired_r,canceled_aw,canceled_w,canceled_ar,reset_events,grant_count);
  foreach(coverage[name])if(coverage[name])$display("PBQ_COVER %s",name);
 endfunction
endclass
