// Original ProtocolBridge integration. Vendor implementation stays on licensed host.
`include "svt_axi.uvm.pkg"
`include "svt_apb.uvm.pkg"
`include "svt_axi_if.svi"
`include "svt_apb_if.svi"
import uvm_pkg::*;
import svt_axi_uvm_pkg::*;
import svt_apb_uvm_pkg::*;
`uvm_analysis_imp_decl(_axi)
`uvm_analysis_imp_decl(_apb)
class bridge_scoreboard extends uvm_scoreboard;
 `uvm_component_utils(bridge_scoreboard)
 uvm_analysis_imp_axi#(svt_axi_transaction,bridge_scoreboard) axi_in;
 uvm_analysis_imp_apb#(svt_apb_transaction,bridge_scoreboard) apb_in;
 svt_axi_transaction intended[$],axiq[$]; svt_apb_transaction apbq[$];
 bit [31:0] mem[bit[31:0]];
 int planned=0,axi_count=0,apb_count=0,checked=0,errors=0;
 function new(string name,uvm_component parent);super.new(name,parent);axi_in=new("axi_in",this);apb_in=new("apb_in",this);endfunction
 function void bad(string why);errors++;$display("PB2_ERROR %s",why);`uvm_error("PB_FUNCTION",why) endfunction
 function void plan(svt_axi_transaction t);
  svt_axi_transaction c; $cast(c,t.clone());intended.push_back(c);planned++;
 endfunction
 function void write_axi(svt_axi_transaction t);
  svt_axi_transaction c;$cast(c,t.clone());axiq.push_back(c);axi_count++;$display("PB2_AXI %0d",axi_count);compare_pending();
 endfunction
 function void write_apb(svt_apb_transaction t);
  svt_apb_transaction c;$cast(c,t.clone());apbq.push_back(c);apb_count++;$display("PB2_APB %0d",apb_count);compare_pending();
 endfunction
 function void compare_pending();
  svt_axi_transaction e,a;svt_apb_transaction p;
  bit wr,err;bit[31:0] addr,rd,mask;
  while(intended.size() && axiq.size() && apbq.size()) begin
   e=intended.pop_front();a=axiq.pop_front();p=apbq.pop_front();
   addr=e.addr;wr=e.xact_type==svt_axi_transaction::WRITE;err=addr[12];
   rd=mem.exists(addr)?mem[addr]:(addr^32'h9e3779b9);
   if(a.addr!==e.addr || a.xact_type!=e.xact_type) bad("AXI observed request differs from plan");
   if(p.address!==e.addr || (p.xact_type==svt_apb_transaction::WRITE)!=wr) bad($sformatf("APB address/direction expected=%08x/%0d actual=%08x/%0d",addr,wr,p.address,p.xact_type==svt_apb_transaction::WRITE));
   if(p.pslverr_enable!=err) bad("APB target response mismatch");
   if(wr) begin
    if(a.data[0]!==e.data[0] || a.wstrb[0]!==e.wstrb[0]) bad("AXI data/strobe mismatch");
    if(p.data[31:0]!==e.data[0][31:0] || p.pstrb[3:0]!==e.wstrb[0][3:0]) bad($sformatf("APB write expected=%08x/%x actual=%08x/%x",e.data[0][31:0],e.wstrb[0][3:0],p.data[31:0],p.pstrb[3:0]));
    if(a.bresp!=(err?svt_axi_transaction::SLVERR:svt_axi_transaction::OKAY)) bad("BRESP mismatch");
    mask=0;for(int k=0;k<4;k++) if(e.wstrb[0][k]) mask[8*k+:8]=8'hff;
    if(!err) mem[addr]=(rd&~mask)|(e.data[0][31:0]&mask);
   end else begin
    if(p.data[31:0]!==rd || a.data[0][31:0]!==rd) bad("Read data mismatch");
    if(a.rresp[0]!=(err?svt_axi_transaction::SLVERR:svt_axi_transaction::OKAY)) bad("RRESP mismatch");
   end
   checked++;
   $display("PB2_CHECK %0d %08x %0d %0d",checked,addr,wr,errors);
  end
 endfunction
 function void report_phase(uvm_phase phase);
  if(planned==0 || planned!=checked || axi_count!=planned || apb_count!=planned) bad("Missing/duplicate transactions");
  $display("PB2_RESULT planned=%0d axi=%0d apb=%0d checked=%0d errors=%0d",planned,axi_count,apb_count,checked,errors);
 endfunction
endclass
class target_sequence extends svt_apb_slave_base_sequence;
 `uvm_object_utils(target_sequence)
 bit[31:0] mem[bit[31:0]];
 function new(string name="target_sequence");super.new(name);endfunction
 task body();
  bit[31:0] addr,rd,mask;int waits;bit err;
  super.body();
  forever begin
   p_sequencer.response_request_port.peek(req);
   if(req.cfg==null) req.cfg=cfg;
   addr=req.address;rd=mem.exists(addr)?mem[addr]:(addr^32'h9e3779b9);err=addr[12];
   waits=addr[6:2]%5;
   req.num_wait_cycles=waits;req.pslverr_enable=err;
   if(req.xact_type==svt_apb_transaction::READ) req.data=rd;
   start_item(req);finish_item(req);
  end
 endtask
endclass
class target_memory extends uvm_subscriber#(svt_apb_transaction);
 `uvm_component_utils(target_memory)
 target_sequence seq;
 function new(string name,uvm_component parent);super.new(name,parent);endfunction
 function void write(svt_apb_transaction t);
  bit[31:0] a,old,mask;
  a=t.address;
  if(t.xact_type==svt_apb_transaction::WRITE && !t.pslverr_enable) begin
   old=seq.mem.exists(a)?seq.mem[a]:(a^32'h9e3779b9);mask=0;
   for(int k=0;k<4;k++) if(t.pstrb[k]) mask[8*k+:8]=8'hff;
   seq.mem[a]=(old&~mask)|(t.data[31:0]&mask);
  end
 endfunction
endclass
class request_sequence extends svt_axi_master_base_sequence;
 `uvm_object_utils(request_sequence)
 bridge_scoreboard sb;svt_axi_master_agent agent;
 function new(string name="request_sequence");super.new(name);endfunction
 task body();
  int fd,n,wr,ad,wd,waits,stall;bit[31:0] addr,d;bit[3:0] st;
  super.body();fd=$fopen("vectors.txt","r");if(!fd) `uvm_fatal("PB_INFRA","Missing vectors")
  while(!$feof(fd)) begin
   n=$fscanf(fd,"%d %h %h %h %d %d %d %d\n",wr,addr,d,st,ad,wd,waits,stall);
   if(n!=8) `uvm_fatal("PB_INFRA","Invalid vector")
   repeat(2) @(posedge tb.clk);
   cfg.default_bready=(stall==0);cfg.default_rready=(stall==0);
   agent.reconfigure(cfg);@(negedge tb.clk);
   req=svt_axi_master_transaction::type_id::create("req");req.port_cfg=cfg;
   start_item(req);
   if(!req.randomize() with {
    xact_type==(local::wr?svt_axi_transaction::WRITE:svt_axi_transaction::READ);
    addr==local::addr;burst_length==1;burst_size==svt_axi_transaction::BURST_SIZE_32BIT;
    data.size()==1;data[0]==local::d;
    if(local::wr) {wstrb.size()==1;wstrb[0]==local::st;} else wstrb.size()==0;
    data_before_addr==(local::wr && local::ad>local::wd);
    reference_event_for_addr_valid_delay==(data_before_addr?svt_axi_transaction::FIRST_WVALID_DATA_BEFORE_ADDR:svt_axi_transaction::PREV_ADDR_HANDSHAKE);
    reference_event_for_first_wvalid_delay==(data_before_addr?svt_axi_transaction::PREV_WRITE_DATA_HANDSHAKE:svt_axi_transaction::WRITE_ADDR_VALID);
    addr_valid_delay==local::ad;
    foreach(wvalid_delay[i]) wvalid_delay[i]==local::wd;
    bready_delay==local::stall;foreach(rready_delay[i]) rready_delay[i]==local::stall;
   }) `uvm_fatal("PB_INFRA","AXI request randomization")
   sb.plan(req);finish_item(req);get_response(rsp);
   if(sb.planned%16==0) begin repeat(5) @(posedge tb.clk);tb.reset_between();end
  end
  $fclose(fd);
 endtask
endclass
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

  ac.master_cfg[0].default_bready=1;ac.master_cfg[0].default_rready=1;
  uvm_config_db#(svt_axi_system_configuration)::set(this,"axi","cfg",ac);
  axi=svt_axi_system_env::type_id::create("axi",this);
  pc=new("pc");pc.paddr_width=svt_apb_system_configuration::PADDR_WIDTH_32;
  pc.pdata_width=svt_apb_system_configuration::PDATA_WIDTH_32;pc.apb4_enable=1;pc.create_sub_cfgs(1);
  pc.is_active=0;pc.slave_cfg[0].is_active=1;
  pc.protocol_checks_coverage_enable=1;pc.slave_cfg[0].protocol_checks_coverage_enable=1;
  uvm_config_db#(svt_apb_system_configuration)::set(this,"apb","cfg",pc);
  apb=svt_apb_system_env::type_id::create("apb",this);
  sb=bridge_scoreboard::type_id::create("sb",this);memory=target_memory::type_id::create("memory",this);
  target=target_sequence::type_id::create("target");memory.seq=target;
 endfunction
 function void connect_phase(uvm_phase phase);
  axi.master[0].monitor.item_observed_port.connect(sb.axi_in);
  apb.slave[0].monitor.item_observed_port.connect(sb.apb_in);
  apb.slave[0].monitor.item_observed_port.connect(memory.analysis_export);
 endfunction
 task run_phase(uvm_phase phase);
  phase.raise_objection(this);wait(tb.rst_n);repeat(5) @(posedge tb.clk);
  requests=request_sequence::type_id::create("requests");requests.sb=sb;requests.agent=axi.master[0];
  fork target.start(apb.slave[0].sequencer); join_none
  requests.start(axi.master[0].sequencer);
  repeat(20) @(posedge tb.clk);
  $display("PB2_DONE");phase.drop_objection(this);
 endtask
endclass
