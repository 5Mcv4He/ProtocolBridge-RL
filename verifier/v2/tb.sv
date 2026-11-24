`timescale 1ns/1ps
`include "vip.sv"
module tb;
 logic clk=0; always #5 clk=~clk;
 logic rst_n=0,done=0;
 wire [31:0] s_awaddr,s_wdata,s_araddr;
 wire [3:0] s_wstrb;
 wire s_awvalid,s_wvalid,s_arvalid,s_bready,s_rready;
 wire s_awready,s_wready,s_arready,s_bvalid,s_rvalid;
 wire [1:0] s_bresp,s_rresp; wire [31:0] s_rdata;
 wire [31:0] paddr,pwdata; wire [3:0] pstrb; wire [2:0] pprot;
 wire psel,penable,pwrite;
 wire [31:0] prdata; wire pready,pslverr;
 bridge dut(.*);
 svt_apb_if vip_if();
 assign vip_if.pclk=clk; assign vip_if.presetn=rst_n;
 assign vip_if.psel=psel; assign vip_if.penable=penable;
 assign vip_if.paddr=paddr; assign vip_if.pwdata=pwdata;
 assign vip_if.pwrite=pwrite; assign vip_if.pstrb=pstrb; assign vip_if.pprot=pprot;



 svt_axi_if axi_if();
 assign axi_if.common_aclk=clk;
 assign axi_if.master_if[0].aresetn=rst_n;
 assign s_awaddr=axi_if.master_if[0].awaddr;
 assign s_awvalid=axi_if.master_if[0].awvalid;
 assign s_wdata=axi_if.master_if[0].wdata;
 assign s_wstrb=axi_if.master_if[0].wstrb;
 assign s_wvalid=axi_if.master_if[0].wvalid;
 assign s_araddr=axi_if.master_if[0].araddr;
 assign s_arvalid=axi_if.master_if[0].arvalid;
 assign s_bready=axi_if.master_if[0].bready;
 assign s_rready=axi_if.master_if[0].rready;
 assign axi_if.master_if[0].awready=s_awready;
 assign axi_if.master_if[0].wready=s_wready;
 assign axi_if.master_if[0].arready=s_arready;
 assign axi_if.master_if[0].bresp=s_bresp;
 assign axi_if.master_if[0].bvalid=s_bvalid;
 assign axi_if.master_if[0].rresp=s_rresp;
 assign axi_if.master_if[0].rvalid=s_rvalid;
 assign axi_if.master_if[0].rdata=s_rdata;
 assign prdata=vip_if.prdata[0]; assign pready=vip_if.pready[0]; assign pslverr=vip_if.pslverr[0];
 initial begin
  if($bits(vip_if.pwdata)!=32 || $bits(vip_if.pstrb)!=4 || $bits(axi_if.master_if[0].wdata)!=32)
   $fatal(1,"PB_INFRA: compiled VIP widths do not match task");
  $display("PB2_WIDTH axi_data=%0d apb_data=%0d apb_strobe=%0d",$bits(axi_if.master_if[0].wdata),$bits(vip_if.pwdata),$bits(vip_if.pstrb));
  uvm_config_db#(svt_axi_vif)::set(null,"uvm_test_top.axi","vif",axi_if);
  uvm_config_db#(svt_apb_vif)::set(null,"uvm_test_top.apb","vif",vip_if);
  run_test("bridge_vip_test");
 end
 initial begin repeat(8) @(negedge clk);rst_n=1;end
 initial begin repeat(40000) @(posedge clk);$display("PB2_TIMEOUT");$finish;end

 task reset_between();
  @(negedge clk);rst_n=0;repeat(8) @(negedge clk);rst_n=1;
  repeat(5) @(negedge clk);
 endtask
 int cycle=0,aw_cycle=-1,w_cycle=-1;
 int aw_first=0,w_first=0,together=0,stalls=0,early=0,waits_seen=0,resets=0;
 bit previous_reset=0;
 int aw_age=0,w_age=0,ar_age=0,launch_age=0,response_age=0;
 bit need_launch=0,need_response=0,completion_credit=0;
 always @(posedge clk) begin
  cycle++;
  if(!rst_n) begin
   if(previous_reset) resets++;
   aw_cycle=-1;w_cycle=-1;aw_age=0;w_age=0;ar_age=0;launch_age=0;response_age=0;
   need_launch=0;need_response=0;completion_credit=0;
  end else begin
   aw_age=(s_awvalid && !s_awready)?aw_age+1:0;
   w_age=(s_wvalid && !s_wready)?w_age+1:0;
   ar_age=(s_arvalid && !s_arready)?ar_age+1:0;
   if(aw_age>16 || w_age>16 || ar_age>16) `uvm_error("PB_TIMING","AXI acceptance exceeded 16 cycles")
   if(s_awvalid && s_awready) aw_cycle=cycle;
   if(s_wvalid && s_wready) w_cycle=cycle;
   if(aw_cycle>=0 && w_cycle>=0) begin
    if(aw_cycle<w_cycle) aw_first++;else if(w_cycle<aw_cycle) w_first++;else together++;
    aw_cycle=-1;w_cycle=-1;need_launch=1;launch_age=0;
   end
   if(s_arvalid && s_arready) begin need_launch=1;launch_age=0;end
   if(need_launch) begin
    launch_age++;if(psel && !penable) need_launch=0;
    else if(launch_age>16) `uvm_error("PB_TIMING","APB launch exceeded 16 cycles")
   end
   if(psel && penable && pready) begin
    need_response=1;response_age=0;completion_credit=1;
    if((pwrite && s_bready)||(!pwrite && s_rready)) early++;
   end
   if((s_bvalid || s_rvalid) && !completion_credit) `uvm_error("PB_TIMING","Response before APB completion")
   if((s_bvalid && s_bready)||(s_rvalid && s_rready)) completion_credit=0;
   if(need_response) begin
    response_age++;if(s_bvalid || s_rvalid) need_response=0;
    else if(response_age>16) `uvm_error("PB_TIMING","AXI response exceeded 16 cycles")
   end
   if((s_bvalid && !s_bready)||(s_rvalid && !s_rready)) stalls++;
   if(psel && penable && !pready) waits_seen++;
  end
  previous_reset=rst_n;
 end
 assert property (@(posedge clk) disable iff(!rst_n) psel && !pwrite |-> pstrb==0) else `uvm_error("PB_TIMING","Read PSTRB must be zero")
 assert property (@(posedge clk) !rst_n |=> !s_bvalid && !s_rvalid && !psel && !penable) else `uvm_error("PB_TIMING","Synchronous reset outputs")
 assert property (@(posedge clk) disable iff(!rst_n) s_bvalid && !s_bready |=> s_bvalid && $stable(s_bresp)) else `uvm_error("PB_TIMING","B response unstable under stall")
 assert property (@(posedge clk) disable iff(!rst_n) s_rvalid && !s_rready |=> s_rvalid && $stable({s_rresp,s_rdata})) else `uvm_error("PB_TIMING","R response unstable under stall")
 assert property (@(posedge clk) disable iff(!rst_n) psel && (!penable || !pready) |=> psel && penable && $stable({paddr,pwrite,pwdata,pstrb,pprot})) else `uvm_error("PB_TIMING","APB setup/access stability")
 assert property (@(posedge clk) disable iff(!rst_n) penable |-> psel) else `uvm_error("PB_TIMING","PENABLE without PSEL")
 final $display("PB2_COVER aw_first=%0d w_first=%0d together=%0d stalls=%0d early=%0d waits=%0d resets=%0d",aw_first,w_first,together,stalls,early,waits_seen,resets);
endmodule
