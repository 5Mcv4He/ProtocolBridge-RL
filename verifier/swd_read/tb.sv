`timescale 1ns/1ps
`include "svt_swd.uvm.pkg"
module top;
 import uvm_pkg::*;import svt_uvm_pkg::*;import svt_swd_uvm_pkg::*;
 svt_swd_if bus();bit clk=0,rst_n=0;always #5 clk=~clk;
 wire d,oe;logic [31:0] value=0;
 assign bus.swd_data=oe?d:1'bz;pullup(bus.swd_data);
 assign bus.reset=rst_n;
 swd_read dut(clk,rst_n,bus.swd_clk,bus.swd_data,value,d,oe);
 integer total,kind[128];logic [31:0] expected[128],changed[128];
 integer pin_reads=0,vip_reads=0,line_resets=0,physical_resets=0;
 bit loaded=0,watch=0;integer current=0;realtime last_rise=0;bit old_oe=0;
 always @(posedge bus.swd_clk)last_rise=$realtime;
 always @(d or oe)begin
  if(rst_n && (oe || old_oe) && ($realtime-last_rise)>100)fail("timing","output changed outside rising-edge allowance");
  old_oe=oe;
 end
 task fail(string category,string why);$display("PB_SWD_MISMATCH %s %s",category,why);$finish;endtask
 initial begin
  integer f,r;f=$fopen("commands.txt","r");r=$fscanf(f,"%d\n",total);
  if(!f||r!=1||total<1||total>128)begin $display("PB_SWD_INFRA input");$finish;end
  for(integer i=0;i<total;i++)begin
   r=$fscanf(f,"%d %h %h\n",kind[i],expected[i],changed[i]);
   if(r!=3||kind[i]<0||kind[i]>2)begin $display("PB_SWD_INFRA row");$finish;end
  end
  loaded=1;
 end
 // This checker decodes pins; it does not read candidate internal state.
 initial begin
  logic [7:0] header;logic [31:0] data;logic parity;integer row;
  wait(loaded);
  repeat(total)begin
   wait(watch);row=current;
   do begin @(posedge bus.swd_clk);#1;end while(!(bus.output_en && bus.swd_data===1'b1));
   header=1;if(oe!==0)fail("timing","drive during request");
   for(integer b=1;b<8;b++)begin
    @(posedge bus.swd_clk);#1;header[b]=bus.swd_data;
    if(oe!==0)fail("timing","drive during request");
   end
   if(header!==8'ha5)begin $display("PB_SWD_INFRA request");$finish;end
   #100;value=changed[row]; // capture must already have happened at Park.
   @(posedge bus.swd_clk);#100;if(oe!==0)fail("timing","first turnaround driven");
   for(integer b=0;b<3;b++)begin
    @(posedge bus.swd_clk);#100;
    if(oe!==1||bus.swd_data!==(b==0))fail("timing","ACK or output ownership");
   end
   parity=0;
   for(integer b=0;b<32;b++)begin
    @(posedge bus.swd_clk);#100;
    if(oe!==1||bus.swd_data!==expected[row][b])fail("data","read payload");
    data[b]=bus.swd_data;parity=parity^bus.swd_data;
   end
   @(posedge bus.swd_clk);#100;
   if(oe!==1||bus.swd_data!==parity)fail("timing","data parity");
   @(posedge bus.swd_clk);#100;if(oe!==0)fail("timing","return turnaround driven");
   pin_reads++;watch=0;
  end
 end
 // Catch persistent ownership outside the packet even if both sides drive 1.
 always @(posedge clk) if(rst_n && oe && bus.output_en)begin
  #100;if(rst_n && oe && bus.output_en)fail("timing","simultaneous bus drivers");
 end
 class seq_t extends uvm_sequence#(svt_swd_transaction);
  `uvm_object_utils(seq_t)
  function new(string n="seq_t");super.new(n);endfunction
  task send(input svt_swd_types::cmd_type_enum command);
   svt_swd_transaction t,r;
   t=svt_swd_transaction::type_id::create("transaction");start_item(t);t.cmd_type=command;t.addr=0;
   if(command==svt_swd_types::USER_CONTROL)begin t.user_defined_data=new[2];foreach(t.user_defined_data[i])t.user_defined_data[i]=0;end
   finish_item(t);get_response(r);
   if(command==svt_swd_types::DEBUG_PORT_READ)begin
    if(r.ack_type!=svt_swd_types::ACK_OK || r.data!==expected[current])fail("data","VIP response identity or data");
    vip_reads++;
   end
  endtask
  task body();
   wait(loaded);
   for(integer i=0;i<total;i++)begin
    current=i;value=expected[i];
    if(kind[i]==2)begin rst_n=0;#1000;if(oe!==0)fail("timing","reset output enable");rst_n=1;#2000;physical_resets++;end
    if(kind[i]!=0)begin send(svt_swd_types::LINE_RESET);send(svt_swd_types::USER_CONTROL);line_resets++;end
    watch=1;send(svt_swd_types::DEBUG_PORT_READ);wait(!watch);
   end
  endtask
 endclass
 class test_t extends uvm_test;
  `uvm_component_utils(test_t)
  svt_swd_master_agent master;
  function new(string n="test_t",uvm_component p=null);super.new(n,p);endfunction
  function void build_phase(uvm_phase phase);
   svt_swd_agent_configuration c;super.build_phase(phase);
   c=svt_swd_agent_configuration::type_id::create("cfg");c.is_active=1;c.device_type=svt_swd_types::SWD_MASTER;
   c.enable_swd_version_2=0;c.WCR_turnaround_period=1;c.clock_period_ps=1000000;c.enable_get_response=1;
   uvm_config_db#(svt_swd_agent_configuration)::set(this,"master","cfg",c);
   master=svt_swd_master_agent::type_id::create("master",this);
  endfunction
  task run_phase(uvm_phase phase);
   seq_t s;phase.raise_objection(this);s=seq_t::type_id::create("s");s.start(master.transaction_seqr);#2000;
   $display("PB_SWD_COMPLETE pins=%0d responses=%0d lines=%0d resets=%0d",pin_reads,vip_reads,line_resets,physical_resets);
   phase.drop_objection(this);
  endtask
 endclass
 initial begin uvm_config_db#(virtual svt_swd_if)::set(null,"uvm_test_top.master*","vif",bus);run_test("test_t");end
 initial begin #10000000;$display("PB_SWD_INFRA watchdog");$finish;end
endmodule
