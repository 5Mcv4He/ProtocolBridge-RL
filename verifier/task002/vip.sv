// Original integration only. Commercial VIP remains on the licensed host.
`include "svt_axi.uvm.pkg"
`include "svt_apb.uvm.pkg"
`include "svt_axi_if.svi"
`include "svt_apb_if.svi"
import uvm_pkg::*;
import svt_axi_uvm_pkg::*;
import svt_apb_uvm_pkg::*;
`uvm_analysis_imp_decl(_axi)
// Reference decoder deliberately uses inclusive range comparisons.
function automatic int expected_target(bit[31:0] a);
 if(a inside {[32'h1000:32'h1fff]}) return 0;
 if(a inside {[32'h8000:32'h9fff]}) return 1;
 if(a inside {[32'h40000000:32'h40000fff]}) return 2;
 return -1;
endfunction
function automatic bit[31:0] expected_local(bit[31:0] a);
 case(expected_target(a))
  0:return a-32'h1000;1:return a-32'h8000;2:return a-32'h40000000;
  default:return 0;
 endcase
endfunction
class bridge_scoreboard extends uvm_scoreboard;
 `uvm_component_utils(bridge_scoreboard)
 uvm_analysis_imp_axi#(svt_axi_transaction,bridge_scoreboard) axi_in;

 svt_axi_transaction expected;
 bit active=0,have_axi=0,have_apb=0,expected_error;
 bit [31:0] mem[bit[31:0]];
 int planned=0,axi_count=0,apb_count=0,checked=0,errors=0,aborted=0,aborted_apb=0;
 int order_seen,wait_seen,stall_seen; int mapped_count=0,unmapped_count=0; int target_count[3];
 function new(string name,uvm_component parent);super.new(name,parent);axi_in=new("axi_in",this);endfunction
 function void bad(string why);errors++;$display("PB2_ERROR %s",why);`uvm_error("PB_FUNCTION",why) endfunction
 function bit[31:0] value_at(bit[31:0] a);return mem.exists(a)?mem[a]:(expected_local(a)^32'h9e3779b9^(expected_target(a)*32'h01010101));endfunction
 function void plan(svt_axi_transaction t,bit err);
  if(active) bad("Overlapping planned transaction");
  $cast(expected,t.clone());active=1;have_axi=0;have_apb=0;expected_error=err;planned++;
 endfunction
 function void finish_if_complete();
  if(have_axi && (have_apb || expected_target(expected.addr)<0)) begin
   checked++;active=0;
   $display("PB2_LATENCY accept_to_setup=%0d completion_to_valid=%0d waits=%0d stalls=%0d",tb.t_setup-tb.t_accept,tb.t_valid-tb.t_complete,tb.tx_waits,tb.tx_stalls);
   if(expected.xact_type==svt_axi_transaction::WRITE)
    $display("PB2_CROSS target=%0d strobe=%0d order=%0d error=%0d wait=%0d stall=%0d",expected_target(expected.addr),expected.wstrb[0][3:0],tb.tx_offer_order,expected_error,(tb.tx_waits==0?0:(tb.tx_waits<=8?1:2)),(tb.tx_stalls>0));
   $display("PB2_CHECK checked=%0d errors=%0d",checked,errors);
  end
 endfunction
 function void write_target(svt_apb_transaction p,int target_index);
  bit wr;bit[31:0] a,old,mask;
  if(!tb.rst_n && tb.reset_stage_active!=0 && tb.t_complete<0) begin $display("PB2_ABORT_NOTICE apb");return;end
  apb_count++;
  if(!active || have_apb) begin bad("Unexpected/duplicate APB completion");return;end
  a=expected.addr;if(expected_target(a)<0 || target_index!=expected_target(a)) bad("APB target mismatch or unmapped side effect");target_count[target_index]++;wr=expected.xact_type==svt_axi_transaction::WRITE;old=value_at(a);
  if(p.address!==expected_local(a) || (p.xact_type==svt_apb_transaction::WRITE)!=wr) bad("APB address/direction mismatch");
  if(p.pslverr_enable!=expected_error) bad("APB error injection not observed");
  if(wr) begin
   if(p.data[31:0]!==expected.data[0][31:0] || p.pstrb[3:0]!==expected.wstrb[0][3:0]) bad("APB write data/strobe mismatch");
   mask=0;for(int k=0;k<4;k++) if(expected.wstrb[0][k]) mask[8*k+:8]=8'hff;
   if(!expected_error) mem[a]=(old&~mask)|(expected.data[0][31:0]&mask);
  end else if(p.data[31:0]!==old) bad("APB read data mismatch");
  have_apb=1;finish_if_complete();
 endfunction
 function void write_axi(svt_axi_transaction a);
  bit wr;
  // AXI VIP publishes interrupted transactions at reset, even without a B/R
  // handshake. Account for these notices separately from completed transfers.
  if(!tb.rst_n && tb.reset_stage_active!=0 && tb.tx_handshakes==0) begin
   $display("PB2_ABORT_NOTICE axi status=%0d",a.is_aborted(1));return;
  end
  axi_count++;
  if(!active || have_axi) begin bad("Unexpected/duplicate AXI completion");return;end
  wr=expected.xact_type==svt_axi_transaction::WRITE;
  if(a.addr!==expected.addr || a.xact_type!=expected.xact_type) bad("AXI observed request differs from plan");
  if(wr) begin
   if(a.data[0]!==expected.data[0] || a.wstrb[0]!==expected.wstrb[0]) bad("AXI write data/strobe mismatch");
   if(a.bresp!=(expected_target(expected.addr)<0?svt_axi_transaction::DECERR:(expected_error?svt_axi_transaction::SLVERR:svt_axi_transaction::OKAY))) bad("BRESP mismatch");
  end else begin
   if(a.data[0][31:0]!==(expected_target(expected.addr)<0?32'b0:value_at(expected.addr))) bad("AXI read data mismatch");
   if(a.rresp[0]!=(expected_target(expected.addr)<0?svt_axi_transaction::DECERR:(expected_error?svt_axi_transaction::SLVERR:svt_axi_transaction::OKAY))) bad("RRESP mismatch");
  end
  if(expected_target(expected.addr)<0) unmapped_count++;else mapped_count++;have_axi=1;finish_if_complete();
 endfunction
 function void abort_transaction(int stage);
  if(!active || have_axi) bad("Reset abort did not interrupt an active transaction");
  if(have_apb!=((stage==7 || stage==8) && expected_target(expected.addr)>=0)) bad("Reset stage/APB completion mismatch");
  aborted++;if(have_apb) aborted_apb++;active=0;have_apb=0;have_axi=0;
  $display("PB2_RESET stage=%0d",stage);
 endfunction
 function void report_phase(uvm_phase phase);
  if(planned==0 || active || planned!=checked+aborted || axi_count!=checked || apb_count!=mapped_count+aborted_apb) bad("Missing/duplicate/unaccounted transactions");
  $display("PB2_ROUTE mapped=%0d unmapped=%0d target0=%0d target1=%0d target2=%0d",mapped_count,unmapped_count,target_count[0],target_count[1],target_count[2]);
  $display("PB2_RESULT planned=%0d axi=%0d apb=%0d checked=%0d aborted=%0d aborted_apb=%0d errors=%0d",planned,axi_count,apb_count,checked,aborted,aborted_apb,errors);
 endfunction
endclass
class target_sequence extends svt_apb_slave_base_sequence;
 `uvm_object_utils(target_sequence)
 bit[31:0] mem[bit[31:0]];int target_index;
 function new(string name="target_sequence");super.new(name);endfunction
 task body();
  bit[31:0] addr;super.body();
  forever begin
   p_sequencer.response_request_port.peek(req);
   if(req.cfg==null) req.cfg=cfg;
   addr=req.address;req.num_wait_cycles=tb.target_wait;req.pslverr_enable=tb.target_error;
   if(req.xact_type==svt_apb_transaction::READ) req.data=mem.exists(addr)?mem[addr]:(addr^32'h9e3779b9^(target_index*32'h01010101));
   start_item(req);finish_item(req);
   if(!tb.rst_n) wait(tb.rst_n);
  end
 endtask
endclass
class target_memory extends uvm_subscriber#(svt_apb_transaction);
 `uvm_component_utils(target_memory)
 target_sequence seq;bridge_scoreboard sb;int target_index;
 function new(string name,uvm_component parent);super.new(name,parent);endfunction
 function void write(svt_apb_transaction t);
  bit[31:0] a,old,mask;a=t.address;sb.write_target(t,target_index);
  if(t.xact_type==svt_apb_transaction::WRITE && !t.pslverr_enable) begin
   old=seq.mem.exists(a)?seq.mem[a]:(a^32'h9e3779b9^(target_index*32'h01010101));mask=0;
   for(int k=0;k<4;k++) if(t.pstrb[k]) mask[8*k+:8]=8'hff;
   seq.mem[a]=(old&~mask)|(t.data[31:0]&mask);
  end
 endfunction
endclass
class one_request_sequence extends svt_axi_master_base_sequence;
 `uvm_object_utils(one_request_sequence)
 bridge_scoreboard sb;svt_axi_port_configuration active_cfg;
 bit wr,err;bit[31:0] addr,data;bit[3:0] strobe;int ad,wd,stall;
 function new(string name="one_request_sequence");super.new(name);endfunction
 task body();
  super.body();cfg=active_cfg;set_response_queue_error_report_disabled(1);
  req=svt_axi_master_transaction::type_id::create("req");req.port_cfg=cfg;
  start_item(req);
  if(!req.randomize() with {
   xact_type==(local::wr?svt_axi_transaction::WRITE:svt_axi_transaction::READ);
   addr==local::addr;burst_length==1;burst_size==svt_axi_transaction::BURST_SIZE_32BIT;
   data.size()==1;data[0]==local::data;
   if(local::wr) {wstrb.size()==1;wstrb[0]==local::strobe;} else wstrb.size()==0;
   data_before_addr==(local::wr && local::ad>local::wd);
   reference_event_for_addr_valid_delay==(data_before_addr?svt_axi_transaction::FIRST_WVALID_DATA_BEFORE_ADDR:svt_axi_transaction::PREV_ADDR_HANDSHAKE);
   reference_event_for_first_wvalid_delay==(data_before_addr?svt_axi_transaction::PREV_WRITE_DATA_HANDSHAKE:svt_axi_transaction::WRITE_ADDR_VALID);
   addr_valid_delay==(local::ad>0?6:0);foreach(wvalid_delay[i]) wvalid_delay[i]==(local::wd>0?6:0);
   reference_event_for_bready_delay==svt_axi_transaction::BVALID;
   reference_event_for_rready_delay==svt_axi_transaction::RVALID;
   bready_delay==(local::stall>0?6:0);foreach(rready_delay[i]) rready_delay[i]==(local::stall>0?6:0);
  }) `uvm_fatal("PB_INFRA","AXI request randomization")
  // Override legal directed delays after randomization: VIP default distribution
  // excludes some long delays and must not silently narrow task coverage.
  req.addr_valid_delay=ad;foreach(req.wvalid_delay[i]) req.wvalid_delay[i]=wd;
  req.bready_delay=stall;foreach(req.rready_delay[i]) req.rready_delay[i]=stall;
  sb.plan(req,err);finish_item(req);get_response(rsp);
 endtask
endclass
class request_sequence extends svt_axi_master_base_sequence;
 `uvm_object_utils(request_sequence)
 bridge_scoreboard sb;svt_axi_master_agent agent;
 
 function new(string name="request_sequence");super.new(name);endfunction
 virtual function bit permits_abort();return 0;endfunction
 task body();
  int fd,n,wr,ad,wd,waits,stall,err,stage,gap;bit[31:0] addr,d;bit[3:0] st;
  one_request_sequence one;
  super.body();fd=$fopen("vectors.txt","r");if(!fd) `uvm_fatal("PB_INFRA","Missing vectors")
  $display("PB2_SEQUENCE %s",get_type_name());
  while(!$feof(fd)) begin
   n=$fscanf(fd,"%d %h %h %h %d %d %d %d %d %d %d\n",wr,addr,d,st,ad,wd,waits,stall,err,stage,gap);
   if(n!=11) `uvm_fatal("PB_INFRA","Invalid vector")
   if(stage && !permits_abort()) `uvm_fatal("PB_INFRA","Abort requires reset sequence")
   repeat(2+gap) @(posedge tb.clk);
   @(negedge tb.clk);tb.clear_transaction();tb.target_wait=waits;tb.target_error=err;
   one=one_request_sequence::type_id::create("one");
   one.sb=sb;one.active_cfg=cfg;one.wr=wr;one.err=err;one.addr=addr;one.data=d;one.strobe=st;one.ad=ad;one.wd=wd;one.stall=stall;
   if(!stage) one.start(p_sequencer);
   else begin
    fork : attempt
     one.start(p_sequencer);
     begin
      tb.wait_reset_stage(stage%100);
      repeat(stage/100) @(negedge tb.clk);
      @(negedge tb.clk);tb.reset_stage_active=stage%100;tb.rst_n=0;
      one.kill(); // APB driver owns its reset cancellation and item_done pairing.
      sb.abort_transaction(stage%100);
      $display("PB2_RESET_OFFSET cycles=%0d",stage/100);
      repeat(8) @(negedge tb.clk);tb.rst_n=1;
      repeat(5) @(negedge tb.clk);tb.reset_stage_active=0;
     end
    join_any
    // The one-request child can finish because of reset before the reset branch;
    // wait for reset recovery before issuing another transaction.
    if(!tb.rst_n) wait(tb.rst_n);
    repeat(8) @(negedge tb.clk);
   end
  end
  $fclose(fd);
 endtask
endclass
`define PB_SEQUENCE(NAME) \
class NAME extends request_sequence; \
 `uvm_object_utils(NAME) \
 function new(string name=`"NAME`");super.new(name);endfunction \
endclass
`PB_SEQUENCE(address_data_sequence)
`PB_SEQUENCE(memory_pattern_sequence)
`PB_SEQUENCE(strobe_cross_sequence)
`PB_SEQUENCE(channel_order_sequence)
`PB_SEQUENCE(wait_error_sequence)
`PB_SEQUENCE(backpressure_sequence)
`PB_SEQUENCE(mixed_random_sequence)
class reset_abort_sequence extends request_sequence;
 `uvm_object_utils(reset_abort_sequence)
 function new(string name="reset_abort_sequence");super.new(name);endfunction
 virtual function bit permits_abort();return 1;endfunction
endclass
class bridge_vip_test extends uvm_test;
 `uvm_component_utils(bridge_vip_test)
 svt_axi_system_env axi;svt_apb_system_env apb[3];
 bridge_scoreboard sb;target_memory memory[3];
 svt_axi_system_configuration ac;svt_apb_system_configuration pc;
 target_sequence target[3];request_sequence requests;
 function new(string name="bridge_vip_test",uvm_component parent=null);super.new(name,parent);endfunction
 function void build_phase(uvm_phase phase);
  super.build_phase(phase);
  ac=new("ac");ac.create_sub_cfgs(1,0);ac.system_monitor_enable=0;
  ac.master_cfg[0].axi_interface_type=svt_axi_port_configuration::AXI4_LITE;
  ac.master_cfg[0].addr_width=32;ac.master_cfg[0].data_width=32;ac.master_cfg[0].is_active=1;
  ac.master_cfg[0].num_outstanding_xact=1;
  ac.master_cfg[0].awlen_enable=0;
  ac.master_cfg[0].arlen_enable=0;
  ac.master_cfg[0].awsize_enable=0;
  ac.master_cfg[0].arsize_enable=0;
  ac.master_cfg[0].awburst_enable=0;
  ac.master_cfg[0].arburst_enable=0;
  ac.master_cfg[0].awlock_enable=0;
  ac.master_cfg[0].arlock_enable=0;
  ac.master_cfg[0].awcache_enable=0;
  ac.master_cfg[0].arcache_enable=0;
  ac.master_cfg[0].wlast_enable=0;
  ac.master_cfg[0].rlast_enable=0;

  // Idle READY is configured once per simulation. Dynamically changing this
  // while a VIP response thread waits for its next transfer can affect the
  // following transfer instead of the intended one.
  ac.master_cfg[0].default_bready=$test$plusargs("PB_READY_EARLY");
  ac.master_cfg[0].default_rready=ac.master_cfg[0].default_bready;
  uvm_config_db#(svt_axi_system_configuration)::set(this,"axi","cfg",ac);
  axi=svt_axi_system_env::type_id::create("axi",this);
  sb=bridge_scoreboard::type_id::create("sb",this);
  for(int i=0;i<3;i++) begin
   pc=new($sformatf("pc%0d",i));pc.paddr_width=svt_apb_system_configuration::PADDR_WIDTH_32;
   pc.pdata_width=svt_apb_system_configuration::PDATA_WIDTH_32;pc.apb4_enable=1;pc.create_sub_cfgs(1);
   pc.is_active=0;pc.slave_cfg[0].is_active=1;
   pc.protocol_checks_coverage_enable=1;pc.slave_cfg[0].protocol_checks_coverage_enable=1;
   uvm_config_db#(svt_apb_system_configuration)::set(this,$sformatf("apb%0d",i),"cfg",pc);
   apb[i]=svt_apb_system_env::type_id::create($sformatf("apb%0d",i),this);
   memory[i]=target_memory::type_id::create($sformatf("memory%0d",i),this);
   target[i]=target_sequence::type_id::create($sformatf("target%0d",i));
   target[i].target_index=i;memory[i].seq=target[i];memory[i].target_index=i;memory[i].sb=sb;
  end
 endfunction
 function void connect_phase(uvm_phase phase);
  axi.master[0].monitor.item_observed_port.connect(sb.axi_in);
  for(int i=0;i<3;i++) apb[i].slave[0].monitor.item_observed_port.connect(memory[i].analysis_export);
 endfunction
 task run_phase(uvm_phase phase);
  phase.raise_objection(this);wait(tb.rst_n);repeat(5) @(posedge tb.clk);
  begin
   string seq_name;uvm_object obj;uvm_factory factory;
   if(!$value$plusargs("PB_SEQUENCE=%s",seq_name)) seq_name="address_data_sequence";
   factory=uvm_factory::get();obj=factory.create_object_by_name(seq_name,"","requests");
   if(!$cast(requests,obj)) `uvm_fatal("PB_INFRA","Invalid sequence type")
  end
  requests.sb=sb;requests.agent=axi.master[0];
  fork target[0].start(apb[0].slave[0].sequencer);target[1].start(apb[1].slave[0].sequencer);target[2].start(apb[2].slave[0].sequencer); join_none
  requests.start(axi.master[0].sequencer);
  repeat(20) @(posedge tb.clk);
  $display("PB2_DONE");phase.drop_objection(this);
 endtask
endclass
