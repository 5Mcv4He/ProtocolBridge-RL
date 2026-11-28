// Project-authored qualification probe. Vendor libraries are external inputs.
`timescale 1ns/1ps
`include "uvm_macros.svh"
`include "svt_apb.uvm.pkg"
`include "svt_apb_if.svi"
import uvm_pkg::*;
import svt_uvm_pkg::*;
import svt_apb_uvm_pkg::*;

// A deliberately small synchronous object. Faults change behavior, not verdicts.
module probe_register(
 input logic clk,rst_n,psel,penable,pwrite,
 input logic [31:0] paddr,pwdata,input logic [3:0] pstrb,
 output logic [31:0] prdata,output logic pready,pslverr
);
 logic [31:0] value;integer waited;integer fault=0;
 initial void'($value$plusargs("fault=%d",fault));
 assign pready=psel && penable && (fault==2 || waited>=2);
 assign pslverr=paddr!=0 && fault!=3;
 assign prdata=paddr==0?value:0;
 always_ff @(posedge clk) begin
  if(!rst_n) begin value<=32'h12345678;waited<=0;end
  else begin
   if(!psel || !penable || pready) waited<=0;else waited<=waited+1;
   if(psel && penable && pready && pwrite && paddr==0)
    for(int k=0;k<4;k++) if(pstrb[k] || fault==1) value[k*8+:8]<=pwdata[k*8+:8];
  end
 end
endmodule

class probe_sequence extends svt_apb_master_base_sequence;
 `uvm_object_utils(probe_sequence)
 function new(string name="probe_sequence");super.new(name);endfunction
 virtual task body();
  svt_apb_master_transaction t;
  super.body();
  for(int i=0;i<6;i++) begin
   t=svt_apb_master_transaction::type_id::create($sformatf("request_%0d",i));
   start_item(t);
   t.cfg=cfg;t.address=(i==3)?32'h100:0;
   t.xact_type=(i==1 || i==4)?svt_apb_transaction::WRITE:svt_apb_transaction::READ;
   t.data=(i==1)?32'ha1b2c3d4:32'h55aa9966;
   t.pstrb=(i==1)?4'h5:((i==4)?4'hf:0);
   finish_item(t);get_response(rsp);
  end
 endtask
endclass

class probe_test extends uvm_test;
 `uvm_component_utils(probe_test)
 svt_apb_system_env apb;
 function new(string name,uvm_component parent);super.new(name,parent);endfunction
 function void build_phase(uvm_phase phase);
  svt_apb_system_configuration c;
  super.build_phase(phase);c=new("master_config");
  c.paddr_width=svt_apb_system_configuration::PADDR_WIDTH_32;
  c.pdata_width=svt_apb_system_configuration::PDATA_WIDTH_32;
  c.apb4_enable=1;c.create_sub_cfgs(1);c.is_active=1;c.slave_cfg[0].is_active=0;
  c.enable_xml_gen=0;c.slave_cfg[0].enable_xml_gen=0;
  uvm_config_db#(svt_apb_system_configuration)::set(this,"apb","cfg",c);
  apb=svt_apb_system_env::type_id::create("apb",this);
 endfunction
 task run_phase(uvm_phase phase);
  probe_sequence seq;
  phase.raise_objection(this);wait(tb.rst_n);repeat(4) @(posedge tb.clk);
  seq=probe_sequence::type_id::create("seq");seq.start(apb.master.sequencer);
  repeat(8) @(posedge tb.clk);
  if(tb.checked!=6 || tb.wait_cycles<12) `uvm_fatal("PB_INFRA","Expected real activity was not observed")
  $display("PB_ROLE_DONE transfers=%0d waits=%0d",tb.checked,tb.wait_cycles);
  phase.drop_objection(this);
 endtask
endclass

module tb;
 logic clk=0,rst_n=0;always #5 clk=~clk;
 svt_apb_if bus();
 wire [31:0] prdata;wire pready,pslverr;
 assign bus.pclk=clk;assign bus.presetn=rst_n;
 assign bus.slave_if[0].prdata=prdata;assign bus.slave_if[0].pready=pready;assign bus.slave_if[0].pslverr=pslverr;
 probe_register dut(clk,rst_n,bus.psel[0],bus.penable,bus.pwrite,bus.paddr,bus.pwdata,bus.pstrb,prdata,pready,pslverr);
 int checked=0,wait_cycles=0,current_waits=0;
 // Six independently written semantic anchors, not DUT memory introspection.
 always @(posedge clk) if(rst_n && bus.psel[0] && bus.penable) begin
  if(!pready) begin current_waits++;wait_cycles++;end
  else begin
   if(current_waits!=2) `uvm_error("PB_TIMING","Expected two Access wait edges")
   if(bus.pwrite !== (checked==1 || checked==4) || bus.paddr !== ((checked==3)?32'h100:32'h0))
    `uvm_error("PB_FUNCTION","Master request identity differs from declared sequence")
   if(pslverr !== (checked==3)) `uvm_error("PB_FUNCTION","Unmapped response error mismatch")
   case(checked)
    0:if(prdata!==32'h12345678) `uvm_error("PB_FUNCTION","Reset data mismatch")
    1:if(bus.pwdata!==32'ha1b2c3d4 || bus.pstrb!==4'h5) `uvm_error("PB_FUNCTION","Byte-write stimulus mismatch")
    2:if(prdata!==32'h12b256d4) `uvm_error("PB_FUNCTION","Byte enable preservation mismatch")
    3:if(prdata!==0) `uvm_error("PB_FUNCTION","Unmapped read value mismatch")
    4:if(bus.pwdata!==32'h55aa9966 || bus.pstrb!==4'hf) `uvm_error("PB_FUNCTION","Full-write stimulus mismatch")
    5:if(prdata!==32'h55aa9966) `uvm_error("PB_FUNCTION","Full-write readback mismatch")
    default:`uvm_error("PB_FUNCTION","Duplicate completion")
   endcase
   checked++;current_waits=0;
  end
 end
 initial begin repeat(8) @(negedge clk);rst_n=1;end
 initial begin repeat(3000) @(posedge clk);$display("PB_ROLE_TIMEOUT");$finish;end
 initial begin
  uvm_config_db#(svt_apb_vif)::set(null,"uvm_test_top.apb","vif",bus);
  run_test("probe_test");
 end
endmodule
