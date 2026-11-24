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
 typedef enum logic [2:0] {IDLE,SETUP,ACCESS,RESP} state_t;
 state_t state;
 logic ah,wh; logic [31:0] addr_buf,data_buf; logic [3:0] strb_buf;
 assign s_awready = rst_n && state==IDLE && !ah;
 assign s_wready = rst_n && state==IDLE && !wh;
 assign s_arready = rst_n && state==IDLE && !ah && !wh;
 assign psel = state==SETUP || state==ACCESS;
 assign penable = state==ACCESS;
 assign pprot = 0;
 always_ff @(posedge clk) begin
  if(!rst_n) begin
   state<=IDLE; ah<=0; wh<=0; s_bvalid<=0; s_rvalid<=0;
   s_bresp<=0; s_rresp<=0; s_rdata<=0; paddr<=0; pwdata<=0; pstrb<=0; pwrite<=0;
   addr_buf<=0; data_buf<=0; strb_buf<=0;
  end else case(state)
   IDLE: begin
    if(s_awvalid && s_awready) begin ah<=1; addr_buf<=s_awaddr; end
    if(s_wvalid && s_wready) begin wh<=1; data_buf<=s_wdata; strb_buf<=s_wstrb; end
    if(ah && wh) begin
     paddr<=addr_buf ^ 32'h4; pwdata<=data_buf; pstrb<=strb_buf; pwrite<=1; state<=SETUP;
    end else if(s_arvalid && s_arready) begin
     paddr<=s_araddr; pwdata<=0; pstrb<=0; pwrite<=0; state<=SETUP;
    end
   end
   SETUP: state<=ACCESS;
   ACCESS: if(pready) begin
    if(pwrite) begin s_bvalid<=1; s_bresp<=pslverr ? 2'b10 : 2'b00; end
    else begin s_rvalid<=1; s_rresp<=pslverr ? 2'b10 : 2'b00; s_rdata<=prdata; end
    state<=RESP;
   end
   RESP: if((s_bvalid && s_bready)||(s_rvalid && s_rready)) begin
    s_bvalid<=0; s_rvalid<=0; ah<=0; wh<=0; state<=IDLE;
   end
   default: state<=IDLE;
  endcase
 end
endmodule
