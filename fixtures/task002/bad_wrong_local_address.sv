module bridge(
 input logic clk,rst_n,
 input logic [31:0] s_awaddr, input logic s_awvalid, output logic s_awready,
 input logic [31:0] s_wdata, input logic [3:0] s_wstrb, input logic s_wvalid, output logic s_wready,
 output logic [1:0] s_bresp, output logic s_bvalid, input logic s_bready,
 input logic [31:0] s_araddr, input logic s_arvalid, output logic s_arready,
 output logic [31:0] s_rdata, output logic [1:0] s_rresp, output logic s_rvalid, input logic s_rready,
 output logic [31:0] paddr,pwdata, output logic [3:0] pstrb, output logic [2:0] pprot,
 output logic [2:0] psel, output logic penable,pwrite, input logic [95:0] prdata, input logic [2:0] pready,pslverr
);
 typedef enum logic [2:0] {IDLE,SETUP,ACCESS,RESP} state_t;
 state_t state;
 logic [1:0] target;
 function automatic logic [1:0] route(input logic [31:0] a);
  if(a>=32'h1000 && a<32'h2000) route=0;
  else if(a>=32'h8000 && a<32'ha000) route=1;
  else if(a>=32'h40000000 && a<32'h40001000) route=2;
  else route=3;
 endfunction
 function automatic logic [31:0] local_address(input logic [31:0] a);
  case(route(a))
   0: local_address=a-32'h1000;
   1: local_address=a;
   2: local_address=a-32'h40000000;
   default: local_address=0;
  endcase
 endfunction
 logic ah,wh; logic [31:0] addr_buf,data_buf; logic [3:0] strb_buf;
 assign s_awready = rst_n && state==IDLE && !ah;
 assign s_wready = rst_n && state==IDLE && !wh;
 assign s_arready = rst_n && state==IDLE && !ah && !wh;
 assign psel = (state==SETUP || state==ACCESS) ? (3'b001 << target) : 3'b000;
 assign penable = state==ACCESS;
 assign pprot = 0;
 always_ff @(posedge clk) begin
  if(!rst_n) begin
   state<=IDLE; target<=0; ah<=0; wh<=0; s_bvalid<=0; s_rvalid<=0;
   s_bresp<=0; s_rresp<=0; s_rdata<=0; paddr<=0; pwdata<=0; pstrb<=0; pwrite<=0;
   addr_buf<=0; data_buf<=0; strb_buf<=0;
  end else case(state)
   IDLE: begin
    if(s_awvalid && s_awready) begin ah<=1; addr_buf<=s_awaddr; end
    if(s_wvalid && s_wready) begin wh<=1; data_buf<=s_wdata; strb_buf<=s_wstrb; end
    if(ah && wh) begin
     paddr<=local_address(addr_buf); target<=route(addr_buf); pwdata<=data_buf; pstrb<=strb_buf; pwrite<=1;
     if(route(addr_buf)==3) begin s_bvalid<=1; s_bresp<=2'b11; state<=RESP; end
     else state<=SETUP;
    end else if(s_arvalid && s_arready) begin
     paddr<=local_address(s_araddr); target<=route(s_araddr); pwdata<=0; pstrb<=0; pwrite<=0;
     if(route(s_araddr)==3) begin s_rvalid<=1; s_rresp<=2'b11; s_rdata<=0; state<=RESP; end
     else state<=SETUP;
    end
   end
   SETUP: state<=ACCESS;
   ACCESS: if(pready[target]) begin
    if(pwrite) begin s_bvalid<=1; s_bresp<=pslverr[target] ? 2'b10 : 2'b00; end
    else begin s_rvalid<=1; s_rresp<=pslverr[target] ? 2'b10 : 2'b00; s_rdata<=prdata[32*target+:32]; end
    state<=RESP;
   end
   RESP: if((s_bvalid && s_bready)||(s_rvalid && s_rready)) begin
    s_bvalid<=0; s_rvalid<=0; ah<=0; wh<=0; state<=IDLE;
   end
   default: state<=IDLE;
  endcase
 end
endmodule
