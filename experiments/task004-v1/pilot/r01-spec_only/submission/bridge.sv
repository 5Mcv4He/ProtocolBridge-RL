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

 // AXI acceptance queues (capacity 3)
 logic [31:0] aw_q [0:2];
 logic [31:0] wd_q [0:2];
 logic [3:0]  ws_q [0:2];
 logic [31:0] ar_q [0:2];
 logic [1:0]  aw_rd, aw_wr, aw_cnt;
 logic [1:0]  w_rd,  w_wr,  w_cnt;
 logic [1:0]  ar_rd, ar_wr, ar_cnt;

 // Write response queue (capacity 3)
 logic [1:0]  b_q [0:2];
 logic [1:0]  b_rd, b_wr, b_cnt;
 // Read response queue (capacity 3)
 logic [31:0] r_dq [0:2];
 logic [1:0]  r_q [0:2];
 logic [1:0]  r_rd, r_wr, r_cnt;

 // Executor state
 typedef enum logic [1:0] {IDLE, SETUP, ACCESS} state_t;
 state_t state;
 logic       rr;          // 0=READ preference, 1=WRITE preference
 logic [31:0] xaddr, xwdata;
 logic [3:0]  xstrb;
 logic        xwrite;

 // Exposed response regs
 logic [31:0] bresp_r;
 logic [1:0]  bvalid_r;
 logic [31:0] rdata_r;
 logic [1:0]  rresp_r;
 logic        rvalid_r;

 assign s_awready = (aw_cnt < 2'd3);
 assign s_wready  = (w_cnt  < 2'd3);
 assign s_arready = (ar_cnt < 2'd3);

 assign s_bvalid  = bvalid_r;
 assign s_bresp   = bresp_r;
 assign s_rvalid  = rvalid_r;
 assign s_rdata   = rdata_r;
 assign s_rresp   = rresp_r;

 assign paddr  = xaddr;
 assign pwdata = xwdata;
 assign pstrb  = xstrb;
 assign pwrite = xwrite;
 assign pprot  = 3'b0;

 logic aw_accept, w_accept, ar_accept;
 logic have_aw, have_w, have_ar, wr_elig, rd_elig;
 logic do_grant_wr, do_grant_rd, do_grant;

 assign aw_accept = s_awvalid && s_awready;
 assign w_accept  = s_wvalid  && s_wready;
 assign ar_accept = s_arvalid && s_arready;

 assign have_aw = (aw_cnt != 2'd0);
 assign have_w  = (w_cnt  != 2'd0);
 assign have_ar = (ar_cnt != 2'd0);

 assign wr_elig = have_aw && have_w;
 assign rd_elig = have_ar;

 always_comb begin
   do_grant_wr = 1'b0;
   do_grant_rd = 1'b0;
   if (state == IDLE) begin
     if (wr_elig && rd_elig) begin
       if (rr) do_grant_wr = 1'b1; else do_grant_rd = 1'b1;
     end else if (wr_elig) do_grant_wr = 1'b1;
     else if (rd_elig) do_grant_rd = 1'b1;
   end
 end
 assign do_grant = do_grant_wr || do_grant_rd;

 integer i;
 always_ff @(posedge clk) begin
   if (!rst_n) begin
     aw_rd <= 0; aw_wr <= 0; aw_cnt <= 0;
     w_rd  <= 0; w_wr  <= 0; w_cnt  <= 0;
     ar_rd <= 0; ar_wr <= 0; ar_cnt <= 0;
     b_rd  <= 0; b_wr  <= 0; b_cnt  <= 0;
     r_rd  <= 0; r_wr  <= 0; r_cnt  <= 0;
     state <= IDLE;
     rr    <= 1'b0;
     xaddr <= 0; xwdata <= 0; xstrb <= 0; xwrite <= 0;
     bresp_r <= 2'b00; bvalid_r <= 0;
     rdata_r <= 0; rresp_r <= 2'b00; rvalid_r <= 0;
   end else begin
     // --- AXI input acceptance ---
     if (aw_accept) begin
       aw_q[aw_wr] <= s_awaddr;
       aw_wr <= (aw_wr == 2'd2) ? 2'd0 : aw_wr + 2'd1;
     end
     if (w_accept) begin
       wd_q[w_wr] <= s_wdata;
       ws_q[w_wr] <= s_wstrb;
       w_wr <= (w_wr == 2'd2) ? 2'd0 : w_wr + 2'd1;
     end
     if (ar_accept) begin
       ar_q[ar_wr] <= s_araddr;
       ar_wr <= (ar_wr == 2'd2) ? 2'd0 : ar_wr + 2'd1;
     end

     begin : counts
       logic [1:0] awc, wc, arc, bc, rc;
       awc = aw_cnt; wc = w_cnt; arc = ar_cnt; bc = b_cnt; rc = r_cnt;
       if (aw_accept) awc = awc + 2'd1;
       if (w_accept)  wc  = wc  + 2'd1;
       if (ar_accept) arc = arc + 2'd1;
       if (do_grant_wr) begin awc = awc - 2'd1; wc = wc - 2'd1; end
       if (do_grant_rd) arc = arc - 2'd1;
       aw_cnt <= awc; w_cnt <= wc; ar_cnt <= arc;
       b_cnt <= bc; r_cnt <= rc;
     end

     // pointer advance on grant
     if (do_grant_wr) begin
       aw_rd <= (aw_rd == 2'd2) ? 2'd0 : aw_rd + 2'd1;
       w_rd  <= (w_rd  == 2'd2) ? 2'd0 : w_rd  + 2'd1;
     end
     if (do_grant_rd) begin
       ar_rd <= (ar_rd == 2'd2) ? 2'd0 : ar_rd + 2'd1;
     end

     // --- B response presentation (FIFO dequeue) ---
     if (bvalid_r && s_bready) begin
       if (b_cnt != 2'd0) begin
         bvalid_r <= 0;
         b_cnt <= b_cnt - 2'd1;
         b_rd <= (b_rd == 2'd2) ? 2'd0 : b_rd + 2'd1;
       end else begin
         bvalid_r <= 0;
       end
     end
     // --- R response presentation (FIFO dequeue) ---
     if (rvalid_r && s_rready) begin
       if (r_cnt != 2'd0) begin
         rvalid_r <= 0;
         r_cnt <= r_cnt - 2'd1;
         r_rd <= (r_rd == 2'd2) ? 2'd0 : r_rd + 2'd1;
       end else begin
         rvalid_r <= 0;
       end
     end

     // --- APB executor ---
     case (state)
       IDLE: begin
         psel <= 0;
         penable <= 0;
         if (do_grant_wr) begin
           xaddr <= aw_q[aw_rd];
           xwdata <= wd_q[w_rd];
           xstrb <= ws_q[w_rd];
           xwrite <= 1'b1;
           state <= SETUP;
           rr <= 1'b0;
         end else if (do_grant_rd) begin
           xaddr <= ar_q[ar_rd];
           xwdata <= 32'b0;
           xstrb <= 4'b0;
           xwrite <= 1'b0;
           state <= SETUP;
           rr <= 1'b1;
         end
       end
       SETUP: begin
         psel <= 1;
         penable <= 0;
         state <= ACCESS;
       end
       ACCESS: begin
         psel <= 1;
         penable <= 1;
         if (pready) begin
           psel <= 0;
           penable <= 0;
           state <= IDLE;
           if (xwrite) begin
             b_q[b_wr] <= pslverr ? 2'b10 : 2'b00;
             b_wr <= (b_wr == 2'd2) ? 2'd0 : b_wr + 2'd1;
             b_cnt <= b_cnt + 2'd1;
           end else begin
             r_dq[r_wr] <= prdata;
             r_q[r_wr] <= pslverr ? 2'b10 : 2'b00;
             r_wr <= (r_wr == 2'd2) ? 2'd0 : r_wr + 2'd1;
             r_cnt <= r_cnt + 2'd1;
           end
         end
       end
       default: state <= IDLE;
     endcase

     // --- present responses when valid not yet driven & queue nonempty ---
     if (!bvalid_r && b_cnt != 2'd0) begin
       bvalid_r <= 1;
       bresp_r <= b_q[b_rd];
     end
     if (!rvalid_r && r_cnt != 2'd0) begin
       rvalid_r <= 1;
       rdata_r <= r_dq[r_rd];
       rresp_r <= r_q[r_rd];
     end

     // psel/penable default driving already handled; ensure setup drives immediately
   end
 end

endmodule