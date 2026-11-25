`timescale 1ns/1ps
`include "vip.sv"
module tb;
 logic clk=0; always #5 clk=~clk;
 logic rst_n=0,done=0;
 int target_wait=0;bit target_error=0;
 int tx_waits=0,tx_stalls=0,tx_order=-1,tx_aw=-1,tx_w=-1;
 int t_accept=-1,t_setup=-1,t_complete=-1,t_valid=-1;
 int tx_aw_offer=-1,tx_w_offer=-1,tx_offer_order=-1,tx_handshakes=0,reset_stage_active=0;
 task clear_transaction();tx_waits=0;tx_stalls=0;tx_order=-1;tx_aw=-1;tx_w=-1;t_accept=-1;t_setup=-1;t_complete=-1;t_valid=-1;tx_aw_offer=-1;tx_w_offer=-1;tx_offer_order=-1;tx_handshakes=0;endtask

 wire [31:0] s_awaddr,s_wdata,s_araddr;
 wire [3:0] s_wstrb;
 wire s_awvalid,s_wvalid,s_arvalid,s_bready,s_rready;
 wire s_awready,s_wready,s_arready,s_bvalid,s_rvalid;
 wire [1:0] s_bresp,s_rresp; wire [31:0] s_rdata;
 wire [31:0] paddr,pwdata; wire [3:0] pstrb; wire [2:0] pprot;
 wire [2:0] psel;wire penable,pwrite;
 wire [95:0] prdata_bus;wire [2:0] pready_bus,pslverr_bus;
 wire pready=|(pready_bus & psel);
 task wait_reset_stage(int stage);
  case(stage)
   1: wait(tx_aw>=0 && tx_w<0);
   2: wait(tx_w>=0 && tx_aw<0);
   3,4: wait(psel && !penable);
   5,6: wait(psel && penable && !pready);
   7: wait(s_bvalid && !s_bready);
   8: wait(s_rvalid && !s_rready);
   default: `uvm_fatal("PB_INFRA","Unknown reset stage")
  endcase
 endtask
 bridge dut(.prdata(prdata_bus),.pready(pready_bus),.pslverr(pslverr_bus),.*);
 svt_apb_if vip_if[3]();
 for(genvar i=0;i<3;i++) begin: targets
  assign vip_if[i].pclk=clk;assign vip_if[i].presetn=rst_n;
  assign vip_if[i].psel=psel[i];assign vip_if[i].penable=penable && psel[i];
  assign vip_if[i].paddr=paddr;assign vip_if[i].pwdata=pwdata;
  assign vip_if[i].pwrite=pwrite;assign vip_if[i].pstrb=pstrb;assign vip_if[i].pprot=pprot;
  assign pready_bus[i]=psel[i]?vip_if[i].pready[0]:1'b1;
  assign pslverr_bus[i]=(psel[i] && penable && pready_bus[i])?vip_if[i].pslverr[0]:~vip_if[i].pslverr[0];
  assign prdata_bus[32*i+:32]=(psel[i] && penable && pready_bus[i])?vip_if[i].prdata[0]:~vip_if[i].prdata[0];
  initial uvm_config_db#(svt_apb_vif)::set(null,$sformatf("uvm_test_top.apb%0d",i),"vif",vip_if[i]);
 end
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
 initial begin
  if($bits(vip_if[0].pwdata)!=32 || $bits(vip_if[0].pstrb)!=4 || $bits(axi_if.master_if[0].wdata)!=32)
   $fatal(1,"PB_INFRA: compiled VIP widths do not match task");
  $display("PB2_WIDTH axi_data=%0d apb_data=%0d apb_strobe=%0d",$bits(axi_if.master_if[0].wdata),$bits(vip_if[0].pwdata),$bits(vip_if[0].pstrb));
  uvm_config_db#(svt_axi_vif)::set(null,"uvm_test_top.axi","vif",axi_if);
  run_test("bridge_vip_test");
 end
 initial begin repeat(8) @(negedge clk);rst_n=1;end
 initial begin repeat(400000) @(posedge clk);$display("PB2_TIMEOUT");$finish;end

 task reset_between();
  @(negedge clk);rst_n=0;repeat(8) @(negedge clk);rst_n=1;
  repeat(5) @(negedge clk);
 endtask
 int cycle=0,aw_cycle=-1,w_cycle=-1;
 int aw_first=0,w_first=0,together=0,stalls=0,early=0,waits_seen=0,resets=0;
 bit previous_reset=0;
 int aw_age=0,w_age=0,ar_age=0,launch_age=0,response_age=0;
 bit need_launch=0,need_response=0,completion_credit=0;bit[31:0] accepted_aw;bit request_mapped;
 always @(posedge clk) begin
  cycle++;
  if(!rst_n) begin
   if(previous_reset) resets++;
   aw_cycle=-1;w_cycle=-1;aw_age=0;w_age=0;ar_age=0;launch_age=0;response_age=0;
   need_launch=0;need_response=0;completion_credit=0;request_mapped=0;
  end else begin
   if(s_awvalid && tx_aw_offer<0) tx_aw_offer=cycle;
   if(s_wvalid && tx_w_offer<0) tx_w_offer=cycle;
   if(tx_aw_offer>=0 && tx_w_offer>=0) tx_offer_order=(tx_aw_offer==tx_w_offer?0:(tx_aw_offer<tx_w_offer?1:2));
   if((s_bvalid && s_bready)||(s_rvalid && s_rready)) tx_handshakes++;
   aw_age=(s_awvalid && !s_awready)?aw_age+1:0;
   w_age=(s_wvalid && !s_wready)?w_age+1:0;
   ar_age=(s_arvalid && !s_arready)?ar_age+1:0;
   if(aw_age>16 || w_age>16 || ar_age>16) `uvm_error("PB_TIMING","AXI acceptance exceeded 16 cycles")
   if(s_awvalid && s_awready) begin aw_cycle=cycle;tx_aw=cycle;accepted_aw=s_awaddr;end
   if(s_wvalid && s_wready) begin w_cycle=cycle;tx_w=cycle;end
   if(tx_aw>=0 && tx_w>=0) begin tx_order=(tx_aw==tx_w?0:(tx_aw<tx_w?1:2));if(t_accept<0) t_accept=cycle;end
   if(s_arvalid && s_arready) t_accept=cycle;
   if(psel && !penable && t_setup<0) t_setup=cycle;
   if(psel && penable && pready) t_complete=cycle;
   if((s_bvalid || s_rvalid) && t_valid<0) t_valid=cycle;
   if(aw_cycle>=0 && w_cycle>=0) begin
    if(aw_cycle<w_cycle) aw_first++;else if(w_cycle<aw_cycle) w_first++;else together++;
    aw_cycle=-1;w_cycle=-1;request_mapped=expected_target(accepted_aw)>=0;
    if(request_mapped) begin need_launch=1;launch_age=0;end
    else begin completion_credit=1;need_response=1;response_age=0;t_setup=t_accept;t_complete=t_accept;end
   end
   if(s_arvalid && s_arready) begin
    request_mapped=expected_target(s_araddr)>=0;
    if(request_mapped) begin need_launch=1;launch_age=0;end
    else begin completion_credit=1;need_response=1;response_age=0;t_setup=t_accept;t_complete=t_accept;end
   end
   if(psel!=0 && !request_mapped) `uvm_error("PB_FUNCTION","Unmapped APB side effect")
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
   if((s_bvalid && !s_bready)||(s_rvalid && !s_rready)) begin stalls++;tx_stalls++;end
   if(psel && penable && !pready) begin waits_seen++;tx_waits++;end
  end
  previous_reset=rst_n;
 end
 assert property (@(posedge clk) disable iff(!rst_n) psel |-> pprot==0) else `uvm_error("PB_TIMING","PPROT must be zero")
 assert property (@(posedge clk) disable iff(!rst_n) psel && !pwrite |-> pstrb==0) else `uvm_error("PB_TIMING","Read PSTRB must be zero")
 assert property (@(posedge clk) !rst_n |=> !s_bvalid && !s_rvalid && !psel && !penable) else `uvm_error("PB_TIMING","Synchronous reset outputs")
 assert property (@(posedge clk) disable iff(!rst_n) s_bvalid && !s_bready |=> s_bvalid && $stable(s_bresp)) else `uvm_error("PB_TIMING","B response unstable under stall")
 assert property (@(posedge clk) disable iff(!rst_n) s_rvalid && !s_rready |=> s_rvalid && $stable({s_rresp,s_rdata})) else `uvm_error("PB_TIMING","R response unstable under stall")
 assert property (@(posedge clk) disable iff(!rst_n) psel && (!penable || !pready) |=> psel && penable && $stable({psel,paddr,pwrite,pwdata,pstrb,pprot})) else `uvm_error("PB_TIMING","APB setup/access stability")
 assert property (@(posedge clk) disable iff(!rst_n) penable |-> psel) else `uvm_error("PB_TIMING","PENABLE without PSEL")
 assert property (@(posedge clk) disable iff(!rst_n) $onehot0(psel)) else `uvm_error("PB_TIMING","Multiple APB targets selected")
 final $display("PB2_COVER aw_first=%0d w_first=%0d together=%0d stalls=%0d early=%0d waits=%0d resets=%0d",aw_first,w_first,together,stalls,early,waits_seen,resets);
endmodule
