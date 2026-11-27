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
 logic [31:0] aq[0:2],dq[0:2],rq[0:2];
 logic [3:0] sq[0:2];

 logic [1:0] aw_wp, aw_rp, w_wp, w_rp;
 logic [1:0] ar_wp, ar_rp;
 logic [1:0] awq, wq, arq;
 logic [2:0] aw_credit, w_credit, ar_credit;
 logic prefer_read;

 wire apush = s_awvalid && s_awready;
 wire wpush = s_wvalid && s_wready;
 wire rpush = s_arvalid && s_arready;
 wire bpop  = s_bvalid && s_bready;
 wire rpop  = s_rvalid && s_rready;

 assign s_awready = rst_n && (aw_credit != 0) && (awq != 2'd3);
 assign s_wready  = rst_n && (w_credit  != 0) && (wq  != 2'd3);
 assign s_arready = rst_n && (ar_credit != 0) && (arq != 2'd3);

 assign psel = (state==SETUP) || (state==ACCESS);
 assign penable = (state==ACCESS);
 assign pprot = 3'b000;

 wire w_eligible = (awq != 0) && (wq != 0);
 wire r_eligible = (arq != 0);

 logic sel_read, sel_write;
 always_comb begin
  sel_read = 1'b0; sel_write = 1'b0;
  if (state==IDLE) begin
   if (r_eligible && (!w_eligible || prefer_read)) sel_read = 1'b1;
   else if (w_eligible) sel_write = 1'b1;
  end
 end

 logic [1:0] awq_n, wq_n, arq_n;
 logic [2:0] awc_n, wc_n, arc_n;

 always_comb begin
  awq_n = awq; wq_n = wq; arq_n = arq;
  awc_n = aw_credit; wc_n = w_credit; arc_n = ar_credit;
  if (apush) begin awq_n = awq_n + 2'd1; awc_n = awc_n - 3'd1; end
  if (wpush) begin wq_n  = wq_n  + 2'd1; wc_n  = wc_n  - 3'd1; end
  if (rpush) begin arq_n = arq_n + 2'd1; arc_n = arc_n - 3'd1; end
  if (sel_write) begin awq_n = awq_n - 2'd1; wq_n = wq_n - 2'd1; end
  if (sel_read)  begin arq_n = arq_n - 2'd1; end
  if (bpop) awc_n = awc_n + 3'd1;
  if (rpop) arc_n = arc_n + 3'd1;
 end

 always_ff @(posedge clk) begin
  if (!rst_n) begin
   state <= IDLE;
   aw_wp<=0; aw_rp<=0; w_wp<=0; w_rp<=0; ar_wp<=0; ar_rp<=0;
   awq<=0; wq<=0; arq<=0;
   aw_credit<=3; w_credit<=3; ar_credit<=3;
   prefer_read<=1'b1;
   s_bvalid<=0; s_rvalid<=0; s_bresp<=0; s_rresp<=0; s_rdata<=0;
   paddr<=0; pwdata<=0; pstrb<=0; pwrite<=0;
  end else begin
   if (apush) begin aq[aw_wp] <= s_awaddr; aw_wp <= aw_wp + 2'd1; end
   if (wpush) begin dq[w_wp] <= s_wdata; sq[w_wp] <= s_wstrb; w_wp <= w_wp + 2'd1; end
   if (rpush) begin rq[ar_wp] <= s_araddr; ar_wp <= ar_wp + 2'd1; end
   if (sel_write) begin aw_rp <= aw_rp + 2'd1; w_rp <= w_rp + 2'd1; end
   if (sel_read)  begin ar_rp <= ar_rp + 2'd1; end

   awq <= awq_n; wq <= wq_n; arq <= arq_n;
   aw_credit <= awc_n; w_credit <= wc_n; ar_credit <= arc_n;

   if (bpop) s_bvalid <= 1'b0;
   if (rpop) s_rvalid <= 1'b0;

   case (state)
    IDLE: begin
     if (sel_read) begin
      paddr <= rq[ar_rp];
      pwdata <= 32'd0; pstrb <= 4'd0; pwrite <= 1'b0;
      prefer_read <= 1'b0;
      state <= SETUP;
     end else if (sel_write) begin
      paddr <= aq[aw_rp];
      pwdata <= dq[w_rp];
      pstrb  <= sq[w_rp];
      pwrite <= 1'b1;
      prefer_read <= 1'b1;
      state <= SETUP;
     end
    end
    SETUP: state <= ACCESS;
    ACCESS: if (pready) begin
     if (pwrite) begin
      s_bresp <= pslverr ? 2'b10 : 2'b00;
      s_bvalid <= 1'b1;
     end else begin
      s_rresp <= pslverr ? 2'b10 : 2'b00;
      s_rdata <= prdata;
      s_rvalid <= 1'b1;
     end
     state <= RESP;
    end
    RESP: begin
     if (bpop || rpop) begin
      s_bvalid <= 1'b0;
      s_rvalid <= 1'b0;
      state <= IDLE;
     end
    end
    default: state <= IDLE;
   endcase
  end
 end
endmodule
