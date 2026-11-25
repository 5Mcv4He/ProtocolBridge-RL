// Task003 independent request-queue model. No candidate hierarchy is inspected.
class bridge_scoreboard extends uvm_scoreboard;
 `uvm_component_utils(bridge_scoreboard)
 uvm_analysis_imp_axi#(svt_axi_transaction,bridge_scoreboard) axi_in;
 uvm_analysis_imp_apb#(svt_apb_transaction,bridge_scoreboard) apb_in;
 svt_axi_transaction wplans[int],rplans[int],expected;
 int wwait[int],rwait[int];bit werror[int],rerror[int];
 int aq[$],wq[$],rq[$];
 int wi=0,ri=0,wa=0,wd=0,ra=0;
 int planned=0,checked=0,aborted=0,aborted_apb=0,axi_count=0,apb_count=0,errors=0;
 int accepted_aw=0,accepted_w=0,accepted_ar=0,retired_w=0,retired_r=0;
 int canceled_aw=0,canceled_w=0,canceled_ar=0;
 int aw_age=0,w_age=0,ar_age=0,response_age=0;
 int reset_events=0,grant_count=0;
 bit busy=0,active=0,have_axi=0,have_apb=0,apb_completed=0,expected_error=0;
 bit first_after_reset=0;
 bit prefer_read=1,in_reset=1,scheduled=0,old_psel=0;
 bit [31:0] mem[bit[31:0]];
 bit coverage[string];
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
 function void finish_if_complete();
  if(have_axi && have_apb) begin checked++;active=0;$display("PBQ_CHECK checked=%0d",checked);end
 endfunction
 function void write_apb(svt_apb_transaction p);
  bit wr;bit[31:0] a,old,mask;
  if(!tb.rst_n) return; // VIP reset notices are not completion handshakes.
  apb_count++;
  if(!active || have_apb) begin bad("Unexpected or duplicate APB completion");return;end
  a=expected.addr;wr=expected.xact_type==svt_axi_transaction::WRITE;old=value_at(a);
  if(p.address!==a || (p.xact_type==svt_apb_transaction::WRITE)!=wr) bad("APB queue head address/direction mismatch");
  if(p.pslverr_enable!=expected_error) bad("Expected target error not observed");
  if(wr) begin
   if(p.data[31:0]!==expected.data[0][31:0] || p.pstrb[3:0]!==expected.wstrb[0][3:0]) bad("APB queued write data/strobe mismatch");
   mask=0;for(int k=0;k<4;k++) if(expected.wstrb[0][k]) mask[8*k+:8]=8'hff;
   if(!expected_error) mem[a]=(old&~mask)|(expected.data[0][31:0]&mask);
   coverage[$sformatf("strobe_%0d",expected.wstrb[0][3:0])]=1;
  end else if(p.data[31:0]!==old) bad("APB read data differs from independent memory");
  if(expected_error) coverage[wr?"write_error":"read_error"]=1;
  have_apb=1;finish_if_complete();
 endfunction
 function void write_axi(svt_axi_transaction a);
  bit wr;
  if(!tb.rst_n) return;
  axi_count++;
  if(!active || have_axi) begin bad("Unexpected or duplicate AXI completion");return;end
  wr=expected.xact_type==svt_axi_transaction::WRITE;
  if(a.addr!==expected.addr || a.xact_type!=expected.xact_type) bad("AXI response pairing/order mismatch");
  if(wr) begin
   if(a.data[0]!==expected.data[0] || a.wstrb[0]!==expected.wstrb[0]) bad("AXI queued write payload mismatch");
   if(a.bresp!=(expected_error?svt_axi_transaction::SLVERR:svt_axi_transaction::OKAY)) bad("BRESP mismatch");
  end else begin
   if(a.data[0][31:0]!==value_at(expected.addr)) bad("RDATA mismatch");
   if(a.rresp[0]!=(expected_error?svt_axi_transaction::SLVERR:svt_axi_transaction::OKAY)) bad("RRESP mismatch");
  end
  have_axi=1;finish_if_complete();
 endfunction
 function void before_edge();
  int id,discarded;bit ew,er,pop_b,pop_r;
  scheduled=0;old_psel=tb.psel;
  if(!tb.rst_n) begin
   if(!in_reset) begin
    reset_events++;first_after_reset=1;
    discarded=planned-checked-aborted;
    if(discarded<1) `uvm_fatal("PB_INFRA","Reset did not interrupt issued requests")
    aborted+=discarded;if(active && have_apb && !have_axi) aborted_apb++;
    canceled_aw+=aq.size();canceled_w+=wq.size();canceled_ar+=rq.size();
    $display("PBQ_RESET stage=%0d canceled=%0d aw=%0d w=%0d ar=%0d apb_completed=%0d",tb.reset_stage_active,discarded,aq.size(),wq.size(),rq.size(),apb_completed);
    if(aq.size()+rq.size()>1 || wq.size()+rq.size()>1) coverage["reset_queued"]=1;
   end
   aq.delete();wq.delete();rq.delete();wa=wi;wd=wi;ra=ri;
   busy=0;active=0;have_axi=0;have_apb=0;apb_completed=0;prefer_read=1;
   aw_age=0;w_age=0;ar_age=0;response_age=0;in_reset=1;return;
  end
  in_reset=0;
  ew=aq.size()>0 && wq.size()>0;er=rq.size()>0;
  // Selection considers buffered requests before this edge's handshakes.
  if(!busy && (ew || er)) begin
   if(active) `uvm_fatal("PB_INFRA","VIP completion callback did not retire before next grant")
   if(ew && er) coverage["both_eligible"]=1;
   if(first_after_reset && ew && er) coverage["reset_read_preference"]=1;
   first_after_reset=0;
   if(er && (!ew || prefer_read)) begin
    id=rq[0];$cast(expected,rplans[id].clone());expected_error=rerror[id];tb.target_wait=rwait[id];
    if((aq.size()>0)!=(wq.size()>0)) coverage["read_during_partial_write"]=1;
    prefer_read=0;
   end else begin
    id=aq[0];if(id!=wq[0]) bad("Accepted AW/W order mismatch");
    $cast(expected,wplans[id].clone());expected_error=werror[id];tb.target_wait=wwait[id];prefer_read=1;
   end
   tb.target_error=expected_error;busy=1;active=1;have_axi=0;have_apb=0;apb_completed=0;
   scheduled=1;grant_count++;
   $display("PBQ_GRANT write=%0d both=%0d aw=%0d w=%0d ar=%0d",expected.xact_type==svt_axi_transaction::WRITE,ew&&er,aq.size(),wq.size(),rq.size());
  end
  if(tb.psel && tb.penable && tb.pready) begin
   if(!active || apb_completed) bad("Unexpected or duplicate APB pin completion");
   apb_completed=1;response_age=0;
  end
  if((tb.s_bvalid || tb.s_rvalid) && (!busy || !apb_completed)) timing("AXI response before selected APB completion");
  if(tb.s_bvalid && tb.s_rvalid) timing("Two responses simultaneously active");
  if(active && ((tb.s_bvalid && expected.xact_type!=svt_axi_transaction::WRITE) || (tb.s_rvalid && expected.xact_type!=svt_axi_transaction::READ))) bad("Wrong response channel");
  if(apb_completed) begin
   response_age++;if(!tb.s_bvalid && !tb.s_rvalid && response_age>16) timing("AXI response exceeded 16 cycles");
  end
  aw_age=(tb.s_awvalid && !tb.s_awready && aq.size()<2)?aw_age+1:0;
  w_age=(tb.s_wvalid && !tb.s_wready && wq.size()<2)?w_age+1:0;
  ar_age=(tb.s_arvalid && !tb.s_arready && rq.size()<2)?ar_age+1:0;
  if(aw_age>16 || w_age>16 || ar_age>16) timing("Available-credit acceptance exceeded 16 cycles");
  pop_b=tb.s_bvalid && tb.s_bready;pop_r=tb.s_rvalid && tb.s_rready;
  if(pop_b) begin
   if(aq.size()==0 || wq.size()==0) bad("Write response without queued halves");
   else begin id=aq.pop_front();id=wq.pop_front();end
   retired_w++;busy=0;apb_completed=0;
  end
  if(pop_r) begin
   if(rq.size()==0) bad("Read response without queued AR");else id=rq.pop_front();
   retired_r++;busy=0;apb_completed=0;
  end
  if(tb.s_awvalid && tb.s_awready) begin
   if(!wplans.exists(wa)) `uvm_fatal("PB_INFRA","Unplanned AW stimulus")
   else if(tb.s_awaddr!==wplans[wa].addr) `uvm_fatal("PB_INFRA","AW stimulus differs from issued request")
   aq.push_back(wa);wa++;accepted_aw++;
   if(tb.s_bvalid && !tb.s_bready) coverage["intake_during_b_stall"]=1;
   if(tb.s_rvalid && !tb.s_rready) coverage["intake_during_r_stall"]=1;
  end
  if(tb.s_wvalid && tb.s_wready) begin
   if(!wplans.exists(wd)) `uvm_fatal("PB_INFRA","Unplanned W stimulus")
   else if(tb.s_wdata!==wplans[wd].data[0][31:0] || tb.s_wstrb!==wplans[wd].wstrb[0][3:0]) `uvm_fatal("PB_INFRA","W stimulus differs from issued request")
   wq.push_back(wd);wd++;accepted_w++;
  end
  if(tb.s_arvalid && tb.s_arready) begin
   if(!rplans.exists(ra)) `uvm_fatal("PB_INFRA","Unplanned AR stimulus")
   else if(tb.s_araddr!==rplans[ra].addr) `uvm_fatal("PB_INFRA","AR stimulus differs from issued request")
   rq.push_back(ra);ra++;accepted_ar++;
   if(tb.s_bvalid && !tb.s_bready) coverage["intake_during_b_stall"]=1;
   if(tb.s_rvalid && !tb.s_rready) coverage["intake_during_r_stall"]=1;
  end
  if(aq.size()>2 || wq.size()>2 || rq.size()>2) timing("Request capacity exceeded");
  if(aq.size()==2) coverage["aw_full"]=1;
  if(wq.size()==2) coverage["w_full"]=1;
  if(rq.size()==2) coverage["ar_full"]=1;
  if(aq.size()>wq.size()) coverage["aw_ahead"]=1;
  if(wq.size()>aq.size()) coverage["w_ahead"]=1;
  if(rq.size()>0 && (aq.size()>0 || wq.size()>0)) coverage["read_write_overlap"]=1;
  if(tb.psel && tb.penable && !tb.pready) coverage["apb_wait"]=1;
  if(tb.s_bvalid && !tb.s_bready) coverage["b_stall"]=1;
  if(tb.s_rvalid && !tb.s_rready) coverage["r_stall"]=1;
 endfunction
 function void after_edge();
  if(!tb.rst_n) return;
  if(scheduled) begin
   if(tb.psel!==1'b1 || tb.penable!==1'b0) timing("Registered FIFO grant/setup missing");
   if(tb.paddr!==expected.addr || tb.pwrite!==(expected.xact_type==svt_axi_transaction::WRITE)) bad("Arbitration or FIFO head mismatch at setup");
   if(expected.xact_type==svt_axi_transaction::WRITE && (tb.pwdata!==expected.data[0][31:0] || tb.pstrb!==expected.wstrb[0][3:0])) bad("Queued write payload mismatch at setup");
  end else if(!old_psel && tb.psel) bad("APB setup without eligible scheduled request");
 endfunction
 function void report_phase(uvm_phase phase);
  if(planned!=tb.expected_planned) `uvm_fatal("PB_INFRA","Issued stimulus count differs from scenario")
  if(planned==0 || active || busy || aq.size() || wq.size() || rq.size() || planned!=checked+aborted || axi_count!=checked || apb_count!=checked+aborted_apb) bad("Unaccounted queued/response transactions");
  if(accepted_aw!=retired_w+canceled_aw || accepted_w!=retired_w+canceled_w || accepted_ar!=retired_r+canceled_ar) bad("Request credit ledger mismatch");
  $display("PBQ_RESULT planned=%0d axi=%0d apb=%0d checked=%0d aborted=%0d aborted_apb=%0d errors=%0d",planned,axi_count,apb_count,checked,aborted,aborted_apb,errors);
  $display("PBQ_CREDITS aw=%0d w=%0d ar=%0d retired_w=%0d retired_r=%0d canceled_aw=%0d canceled_w=%0d canceled_ar=%0d resets=%0d grants=%0d",accepted_aw,accepted_w,accepted_ar,retired_w,retired_r,canceled_aw,canceled_w,canceled_ar,reset_events,grant_count);
  foreach(coverage[name]) if(coverage[name]) $display("PBQ_COVER %s",name);
 endfunction
endclass
