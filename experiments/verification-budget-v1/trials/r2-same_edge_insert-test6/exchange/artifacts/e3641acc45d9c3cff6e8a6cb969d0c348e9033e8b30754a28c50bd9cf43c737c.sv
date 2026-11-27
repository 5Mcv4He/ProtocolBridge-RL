module bridge(
 input logic clk,rst_n,
 input logic [31:0] s_awaddr, input logic s_awvalid, output logic s_awready,
 input logic [31:0] s_wdata, input logic [3:0] s_wstrb, input logic s_wvalid, output logic s_wready,
 output logic [1:0] s_bresp, output logic s_bvalid, input logic s_bready,
 input logic [31:0] s_araddr, input logic s_arvalid, output logic s_arready,
 output logic [31:0] s_rdata, output logic [1:0] s_rresp, output logic s_rvalid, input logic s_rready,
 output logic [31:0] paddr,pwdata, output logic [3:0] pstrb, output logic [2:0] pprot,
 output logic psel,penable,pwrite, input logic [31:0] prdata, input logic pready,pslverr
);
 typedef enum logic [1:0] {IDLE=2'b00,SETUP=2'b01,ACCESS=2'b10,RESP=2'b11} state_t;
 state_t state;
 logic [31:0] aq[0:2],dq[0:2],rq[0:2];
 logic [3:0] sq[0:2];
 logic [2:0] ac,wc,rc;
 logic prefer_read;
 wire apush=s_awvalid && s_awready;
 wire wpush=s_wvalid && s_wready;
 wire rpush=s_arvalid && s_arready;
 wire bpop=s_bvalid && s_bready;
 wire rpop=s_rvalid && s_rready;
 assign s_awready=rst_n && (ac<3 || bpop);
 assign s_wready=rst_n && (wc<3 || bpop);
 assign s_arready=rst_n && (rc<3 || rpop);
 assign psel=state==SETUP || state==ACCESS;
 assign penable=state==ACCESS;
 assign pprot=0;
 always_ff @(posedge clk) begin
  if(!rst_n) begin
   state<=IDLE;ac<=0;wc<=0;rc<=0;
   prefer_read<=1;
   s_bvalid<=0;s_rvalid<=0;s_bresp<=0;s_rresp<=0;s_rdata<=0;
   paddr<=0;pwdata<=0;pstrb<=0;pwrite<=0;
  end else begin
   if(ac>bpop) begin
    for(int i=0;i<2;i++) begin aq[i]<=aq[i+1];dq[i]<=dq[i+1];sq[i]<=sq[i+1];end
   end
   if(rc>rpop) for(int i=0;i<2;i++) rq[i]<=rq[i+1];
   if(apush) begin aq[ac-bpop]<=s_awaddr;dq[ac-bpop]<=s_wdata;sq[ac-bpop]<=s_wstrb;end
   if(rpush) rq[rc-rpop]<=s_araddr;
   ac<=ac+(apush?3'd1:3'd0)-(bpop?3'd1:3'd0);
   wc<=wc+(wpush?3'd1:3'd0)-(bpop?3'd1:3'd0);
   rc<=rc+(rpush?3'd1:3'd0)-(rpop?3'd1:3'd0);
   case(state)
    IDLE: begin
     if(rc>0 && (!(ac>0 && wc>0) || prefer_read)) begin
      paddr<=rq[0];pwdata<=0;pstrb<=0;pwrite<=0;prefer_read<=0;state<=SETUP;
     end else if(ac>0 && wc>0) begin
      paddr<=aq[0];pwdata<=dq[0];pstrb<=sq[0];pwrite<=1;prefer_read<=1;state<=SETUP;
     end
    end
    SETUP:state<=ACCESS;
    ACCESS:if(pready) begin
     if(pwrite) begin s_bresp<=pslverr?2'b10:2'b00;s_bvalid<=1;end
     else begin s_rresp<=pslverr?2'b10:2'b00;s_rdata<=prdata;s_rvalid<=1;end
     state<=RESP;
    end
    RESP:if(bpop || rpop) begin s_bvalid<=0;s_rvalid<=0;state<=IDLE;end
    default:state<=IDLE;
   endcase
  end
 end
endmodule