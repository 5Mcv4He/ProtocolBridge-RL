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
 typedef enum logic [3:0] {IDLE=4'b0001,SETUP=4'b0010,ACCESS=4'b0100,RESP=4'b1000} state_t;
 state_t state;
 logic [31:0] aq[0:2],dq[0:2],rq[0:2];
 logic [3:0] sq[0:2];
 logic [1:0] ac,wc,rc;
 logic prefer_read;

 wire awq_full = (ac==2'd3);
 wire wq_full  = (wc==2'd3);
 wire arq_full = (rc==2'd3);

 assign s_awready = rst_n && !awq_full;
 assign s_wready  = rst_n && !wq_full;
 assign s_arready = rst_n && !arq_full;

 wire apush = s_awvalid && s_awready;
 wire wpush = s_wvalid && s_wready;
 wire rpush = s_arvalid && s_arready;
 wire bpop  = s_bvalid && s_bready;
 wire rpop  = s_rvalid && s_rready;

 assign psel = (state==SETUP) || (state==ACCESS);
 assign penable = (state==ACCESS);
 assign pprot = 3'b000;

 logic [1:0] an,wn,rn;
 logic wen,ren;
 always_comb begin
   an = ac; wn = wc; rn = rc;
   if(bpop) begin an = an - 2'd1; wn = wn - 2'd1; end
   if(rpop) rn = rn - 2'd1;
 end

 always_ff @(posedge clk) begin
  if(!rst_n) begin
   state<=IDLE; ac<=0; wc<=0; rc<=0;
   prefer_read<=1;
   s_bvalid<=0; s_rvalid<=0; s_bresp<=2'b00; s_rresp<=2'b00; s_rdata<=0;
   paddr<=0; pwdata<=0; pstrb<=0; pwrite<=0;
  end else begin
   // queue shifts
   if(bpop) begin
     aq[0]<=aq[1]; aq[1]<=aq[2];
     dq[0]<=dq[1]; dq[1]<=dq[2];
     sq[0]<=sq[1]; sq[1]<=sq[2];
   end
   if(rpop) begin
     rq[0]<=rq[1]; rq[1]<=rq[2];
   end
   // pushes go to position computed from pre-edge state (after any pop adjustment)
   if(apush) begin
     if(bpop) aq[1]<=s_awaddr; else aq[0]<=s_awaddr;
   end
   if(wpush) begin
     if(bpop) begin dq[1]<=s_wdata; sq[1]<=s_wstrb; end
     else begin dq[0]<=s_wdata; sq[0]<=s_wstrb; end
   end
   if(rpush) begin
     if(rpop) rq[1]<=s_araddr; else rq[0]<=s_araddr;
   end

   // count updates
   case({apush,bpop}) 2'b10: ac<=ac+2'd1; 2'b01: ac<=ac-2'd1; default: ac<=ac; endcase
   case({wpush,bpop}) 2'b10: wc<=wc+2'd1; 2'b01: wc<=wc-2'd1; default: wc<=wc; endcase
   case({rpush,rpop}) 2'b10: rc<=rc+2'd1; 2'b01: rc<=rc-2'd1; default: rc<=rc; endcase

   // response defaults - hold until consumed
   // (handled in RESP state below)

   case(state)
    IDLE: begin
     // eligible based on pre-edge buffer contents
     if(rc>0 && (prefer_read || !(ac>0 && wc>0))) begin
       paddr<=rq[0]; pwdata<=0; pstrb<=0; pwrite<=0; prefer_read<=0; state<=SETUP;
     end else if(ac>0 && wc>0) begin
       paddr<=aq[0]; pwdata<=dq[0]; pstrb<=sq[0]; pwrite<=1; prefer_read<=1; state<=SETUP;
     end
    end
    SETUP: state<=ACCESS;
    ACCESS: if(pready) begin
      if(pwrite) begin s_bresp<=pslverr?2'b10:2'b00; s_bvalid<=1; end
      else begin s_rresp<=pslverr?2'b10:2'b00; s_rdata<=prdata; s_rvalid<=1; end
      state<=RESP;
    end
    RESP: if(bpop || rpop) begin s_bvalid<=0; s_rvalid<=0; state<=IDLE; end
    default: state<=IDLE;
   endcase
  end
 end
endmodule
