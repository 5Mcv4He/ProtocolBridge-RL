`timescale 1ns/1ps
`include "vip.sv"
module tb;
 logic clk=0; always #5 clk=~clk;
 logic rst_n=0,done=0;
 int target_wait=0;bit target_error=0;
 bridge_scoreboard sb;int reset_stage_active=0,expected_planned=0;
 wire [31:0] s_awaddr,s_wdata,s_araddr;
 wire [3:0] s_wstrb;
 wire s_awvalid,s_wvalid,s_arvalid,s_bready,s_rready;
 wire s_awready,s_wready,s_arready,s_bvalid,s_rvalid;
 wire [1:0] s_bresp,s_rresp; wire [31:0] s_rdata;
 wire [31:0] paddr,pwdata; wire [3:0] pstrb; wire [2:0] pprot;
 wire psel,penable,pwrite;
 wire [31:0] prdata; wire pready,pslverr;
 task wait_reset_stage(int stage);
  case(stage)
   1:wait(sb.aq.size()==2 && sb.wq.size()==0 && sb.rq.size()>0);
   2:wait(sb.wq.size()==2 && sb.aq.size()==0 && sb.rq.size()>0);
   3:wait(psel && !penable && pwrite);
   4:wait(psel && !penable && !pwrite);
   5:wait(psel && penable && !pready && pwrite && sb.aq.size()==2 && sb.wq.size()==2 && sb.rq.size()==2);
   6:wait(psel && penable && !pready && !pwrite && sb.aq.size()==2 && sb.wq.size()==2 && sb.rq.size()==2);
   7:wait(s_bvalid && !s_bready && sb.aq.size()==2 && sb.wq.size()==2 && sb.rq.size()==2);
   8:wait(s_rvalid && !s_rready && sb.aq.size()==2 && sb.wq.size()==2 && sb.rq.size()==2);
   default:`uvm_fatal("PB_INFRA","Unknown queue reset stage")
  endcase
 endtask
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
 // Response values outside APB completion are deliberately poisoned.
 // Sampling before PREADY must not accidentally pass because data stayed constant.
 assign prdata=(psel && penable && pready)?vip_if.prdata[0]:~vip_if.prdata[0];
 assign pready=vip_if.pready[0];
 assign pslverr=(psel && penable && pready)?vip_if.pslverr[0]:~vip_if.pslverr[0];
 initial begin
  if($bits(vip_if.pwdata)!=32 || $bits(vip_if.pstrb)!=4 || $bits(axi_if.master_if[0].wdata)!=32)
   $fatal(1,"PB_INFRA: compiled VIP widths do not match task");
  $display("PBQ_WIDTH axi_data=%0d apb_data=%0d apb_strobe=%0d",$bits(axi_if.master_if[0].wdata),$bits(vip_if.pwdata),$bits(vip_if.pstrb));
  uvm_config_db#(svt_axi_vif)::set(null,"uvm_test_top.axi","vif",axi_if);
  uvm_config_db#(svt_apb_vif)::set(null,"uvm_test_top.apb","vif",vip_if);
  run_test("bridge_vip_test");
 end
 initial begin repeat(8) @(negedge clk);rst_n=1;end
 initial begin repeat(400000) @(posedge clk);$display("PBQ_TIMEOUT");$finish;end

 always @(posedge clk) begin
  if(sb!=null) begin sb.before_edge();#1;sb.after_edge();end
 end
 assert property (@(posedge clk) disable iff(!rst_n) psel |-> pprot==0) else `uvm_error("PB_TIMING","PPROT must be zero")
 assert property (@(posedge clk) disable iff(!rst_n) psel && !pwrite |-> pstrb==0) else `uvm_error("PB_TIMING","Read PSTRB must be zero")
 assert property (@(posedge clk) !rst_n |=> !s_bvalid && !s_rvalid && !psel && !penable) else `uvm_error("PB_TIMING","Synchronous reset outputs")
 assert property (@(posedge clk) disable iff(!rst_n) s_bvalid && !s_bready |=> s_bvalid && $stable(s_bresp)) else `uvm_error("PB_TIMING","B response unstable under stall")
 assert property (@(posedge clk) disable iff(!rst_n) s_rvalid && !s_rready |=> s_rvalid && $stable({s_rresp,s_rdata})) else `uvm_error("PB_TIMING","R response unstable under stall")
 assert property (@(posedge clk) disable iff(!rst_n) psel && (!penable || !pready) |=> psel && penable && $stable({paddr,pwrite,pwdata,pstrb,pprot})) else `uvm_error("PB_TIMING","APB setup/access stability")
 assert property (@(posedge clk) disable iff(!rst_n) penable |-> psel) else `uvm_error("PB_TIMING","PENABLE without PSEL")
endmodule
