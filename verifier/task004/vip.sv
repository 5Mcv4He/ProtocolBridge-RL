// Original integration only. Commercial VIP remains on the licensed host.
`include "svt_axi.uvm.pkg"
`include "svt_apb.uvm.pkg"
`include "svt_axi_if.svi"
`include "svt_apb_if.svi"
import uvm_pkg::*;
import svt_axi_uvm_pkg::*;
import svt_apb_uvm_pkg::*;
`uvm_analysis_imp_decl(_axi)
`uvm_analysis_imp_decl(_apb)
`include "scoreboard.sv"
class target_sequence extends svt_apb_slave_base_sequence;
 `uvm_object_utils(target_sequence)
 bit[31:0] mem[bit[31:0]];
 function new(string name="target_sequence");super.new(name);endfunction
 task body();
  bit[31:0] addr;super.body();
  forever begin
   p_sequencer.response_request_port.peek(req);
   if(req.cfg==null) req.cfg=cfg;
   addr=req.address;req.num_wait_cycles=tb.target_wait;req.pslverr_enable=tb.target_error;
   if(req.xact_type==svt_apb_transaction::READ) req.data=mem.exists(addr)?mem[addr]:(addr^32'h9e3779b9);
   start_item(req);finish_item(req);
   if(!tb.rst_n) wait(tb.rst_n);
  end
 endtask
endclass
class target_memory extends uvm_subscriber#(svt_apb_transaction);
 `uvm_component_utils(target_memory)
 target_sequence seq;
 function new(string name,uvm_component parent);super.new(name,parent);endfunction
 function void write(svt_apb_transaction t);
  bit[31:0] a,old,mask;a=t.address;
  if(t.xact_type==svt_apb_transaction::WRITE && !t.pslverr_enable) begin
   old=seq.mem.exists(a)?seq.mem[a]:(a^32'h9e3779b9);mask=0;
   for(int k=0;k<4;k++) if(t.pstrb[k]) mask[8*k+:8]=8'hff;
   seq.mem[a]=(old&~mask)|(t.data[31:0]&mask);
  end
 endfunction
endclass
class one_request_sequence extends svt_axi_master_base_sequence;
 `uvm_object_utils(one_request_sequence)
 bridge_scoreboard sb;svt_axi_port_configuration active_cfg;
 bit wr,err;bit[31:0] addr,data;bit[3:0] strobe;int ad,wd,stall,waits,start_delay;
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
  sb.issue(req,err,waits);finish_item(req);get_response(rsp);
 endtask
endclass
class request_sequence extends svt_axi_master_base_sequence;
 `uvm_object_utils(request_sequence)
 bridge_scoreboard sb;svt_axi_master_agent agent;
 function new(string name="request_sequence");super.new(name);endfunction
 task body();
  int fd,n,stage,count,recovery,wr,ad,wd,waits,stall,err,start_delay;
  bit[31:0] addr,data;bit[3:0] st;bit did_reset=0;int completed=0;
  one_request_sequence requests[];
  super.body();fd=$fopen("vectors.txt","r");if(!fd) `uvm_fatal("PB_INFRA","Missing vectors")
  if($fscanf(fd,"%d %d %d\n",stage,count,recovery)!=3 || count<1) `uvm_fatal("PB_INFRA","Invalid batch header")
  tb.expected_planned=count+recovery;requests=new[count+recovery];
  $display("PBQ_SEQUENCE %s",get_type_name());
  for(int i=0;i<count+recovery;i++) begin
   n=$fscanf(fd,"%d %h %h %h %d %d %d %d %d %d\n",wr,addr,data,st,ad,wd,waits,stall,err,start_delay);
   if(n!=10) `uvm_fatal("PB_INFRA","Invalid queue vector")
   requests[i]=one_request_sequence::type_id::create($sformatf("one%0d",i));
   requests[i].sb=sb;requests[i].active_cfg=cfg;requests[i].wr=wr;requests[i].addr=addr;requests[i].data=data;requests[i].strobe=st;
   requests[i].ad=ad;requests[i].wd=wd;requests[i].waits=waits;requests[i].stall=stall;requests[i].err=err;requests[i].start_delay=start_delay;
  end
  $fclose(fd);
  fork : batch
   begin : launch_requests
    for(int i=0;i<count;i++) begin
     automatic int j=i;
     fork
      begin
       repeat(requests[j].start_delay) @(posedge tb.clk);
       requests[j].start(p_sequencer);completed++;
      end
     join_none
    end
    wait(completed==count);
   end
   begin
    if(stage) begin
     tb.wait_reset_stage(stage);
     @(negedge tb.clk);tb.reset_stage_active=stage;tb.rst_n=0;did_reset=1;
     disable launch_requests;
     for(int i=0;i<count;i++) requests[i].kill();
     repeat(8) @(negedge tb.clk);tb.rst_n=1;
     repeat(8) @(negedge tb.clk);tb.reset_stage_active=0;
    end else wait(completed==count);
   end
  join_any
  if(did_reset) begin
   if(!tb.rst_n) wait(tb.rst_n);
   repeat(9) @(negedge tb.clk);
  end
  disable batch;
  if(stage && !did_reset) `uvm_fatal("PB_INFRA","Requested reset trigger was not reached")
  if(stage) begin
   // First post-reset read/write are offered together, checking reset preference.
   fork requests[count].start(p_sequencer);requests[count+1].start(p_sequencer);join
  end
  for(int i=count+(stage?2:0);i<count+recovery;i++) requests[i].start(p_sequencer);
 endtask
endclass
`define PBQ_SEQUENCE(NAME) \
class NAME extends request_sequence; \
 `uvm_object_utils(NAME) \
 function new(string name=`"NAME`");super.new(name);endfunction \
endclass
`PBQ_SEQUENCE(queue_request_sequence)
`PBQ_SEQUENCE(queue_capacity_sequence)
`PBQ_SEQUENCE(queue_partial_sequence)
`PBQ_SEQUENCE(queue_arbitration_sequence)
`PBQ_SEQUENCE(queue_memory_sequence)
`PBQ_SEQUENCE(queue_random_sequence)
`PBQ_SEQUENCE(queue_reset_sequence)
class bridge_vip_test extends uvm_test;
 `uvm_component_utils(bridge_vip_test)
 svt_axi_system_env axi;svt_apb_system_env apb;
 bridge_scoreboard sb;target_memory memory;
 svt_axi_system_configuration ac;svt_apb_system_configuration pc;
 target_sequence target;request_sequence requests;
 function new(string name="bridge_vip_test",uvm_component parent=null);super.new(name,parent);endfunction
 function void build_phase(uvm_phase phase);
  super.build_phase(phase);
  ac=new("ac");ac.create_sub_cfgs(1,0);ac.system_monitor_enable=0;
  ac.master_cfg[0].axi_interface_type=svt_axi_port_configuration::AXI4_LITE;
  ac.master_cfg[0].addr_width=32;ac.master_cfg[0].data_width=32;ac.master_cfg[0].is_active=1;
  ac.master_cfg[0].num_outstanding_xact=12;
  // All offered traffic belongs to the canceled reset epoch, including VIP
  // queued transactions that have not yet asserted a channel VALID.
  ac.master_cfg[0].reset_type=svt_axi_port_configuration::RESET_ALL_XACT;
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
  pc=new("pc");pc.paddr_width=svt_apb_system_configuration::PADDR_WIDTH_32;
  pc.pdata_width=svt_apb_system_configuration::PDATA_WIDTH_32;pc.apb4_enable=1;pc.create_sub_cfgs(1);
  pc.is_active=0;pc.slave_cfg[0].is_active=1;
  pc.protocol_checks_coverage_enable=1;pc.slave_cfg[0].protocol_checks_coverage_enable=1;
  uvm_config_db#(svt_apb_system_configuration)::set(this,"apb","cfg",pc);
  apb=svt_apb_system_env::type_id::create("apb",this);
  sb=bridge_scoreboard::type_id::create("sb",this);tb.sb=sb;memory=target_memory::type_id::create("memory",this);
  target=target_sequence::type_id::create("target");memory.seq=target;
 endfunction
 function void connect_phase(uvm_phase phase);
  axi.master[0].monitor.item_observed_port.connect(sb.axi_in);
  apb.slave[0].monitor.item_observed_port.connect(sb.apb_in);
  apb.slave[0].monitor.item_observed_port.connect(memory.analysis_export);
 endfunction
 task run_phase(uvm_phase phase);
  phase.raise_objection(this);wait(tb.rst_n);repeat(5) @(posedge tb.clk);
  begin
   string seq_name;uvm_object obj;uvm_factory factory;
   if(!$value$plusargs("PB_SEQUENCE=%s",seq_name)) seq_name="queue_request_sequence";
   factory=uvm_factory::get();obj=factory.create_object_by_name(seq_name,"","requests");
   if(!$cast(requests,obj)) `uvm_fatal("PB_INFRA","Invalid sequence type")
  end
  requests.sb=sb;requests.agent=axi.master[0];
  fork target.start(apb.slave[0].sequencer); join_none
  requests.start(axi.master[0].sequencer);
  repeat(20) @(posedge tb.clk);
  $display("PBQ_DONE");phase.drop_objection(this);
 endtask
endclass
