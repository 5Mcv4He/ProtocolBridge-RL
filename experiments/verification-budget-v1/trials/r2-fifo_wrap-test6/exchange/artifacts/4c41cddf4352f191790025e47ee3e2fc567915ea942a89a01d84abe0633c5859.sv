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

 // AXI-side write-side storage: AW and W accepted independently, FIFO per channel.
 // aw_wp: next AW write slot; aw_rp: oldest unretired AW slot (removed at B handshake)
 // w_wp : next W write slot; w_rp : oldest W slot waiting to be consumed by execution
 logic [1:0] aw_wp, aw_rp, w_wp, w_rp;
 logic [1:0] ar_wp, ar_rp;
 logic [1:0] aw_cnt, w_cnt, ar_cnt;

 // progress tracking for write: a write is eligible when aw_cnt>0 && w_cnt>0
 // when a write is started, AW and W payloads consumed for APB execution; but AW
 // credit retires only at B handshake. So track number of AW issued for execution.
 // aw_cnt = accepted AW minus retired AW (at B). aw_rp points to oldest AW not yet
 // turned into APB; aw_rp advances when APB write starts.
 // For W: w_rp advances when APB write starts (W payload consumed).
 // w_cnt = accepted W minus consumed W. But B retire uses AW side. Separate counts:
 // aw_pending (not yet issued to APB) = derived from aw_rp vs aw_wp. Use aw_rp
 // advancing on APB start; aw_wp on accept. Similarly ar.

 logic prefer_read;

 wire apush = s_awvalid && s_awready;
 wire wpush = s_wvalid && s_wready;
 wire rpush = s_arvalid && s_arready;
 wire bpop  = s_bvalid && s_bready;
 wire rpop  = s_rvalid && s_rready;

 logic aw_have, w_have, ar_have;
 assign aw_have = (aw_wp != aw_rp);
 assign w_have  = (w_wp  != w_rp);
 assign ar_have = (ar_wp != ar_rp);

 // number outstanding AW (accepted, not yet issued to APB) for capacity
 logic [1:0] aw_out, w_out, ar_out;
 always_comb begin
  aw_out = aw_wp - aw_rp;
  w_out  = w_wp  - w_rp;
  ar_out = ar_wp - ar_rp;
 end

 // AW/W/AR acceptance must be independent. aw_out counts un-issued AW; but W halves for
 // already-issued writes could still need storage. Since a write begins only when both
 // halves available, and both are consumed together at APB start, count of stored halves
 // is exactly aw_out (AW not yet issued) and w_out (W not yet issued). But also need to
 // store W that arrives before AW pairs: covered by w_out.
 // Capacity: up to 3 unretired AW and 3 W. 'out' counts those not yet issued to APB.
 // Also writes in flight/awaiting B still hold credits but are not in queue. Need total
 // unretired AW = aw_out + in-flight (APB executing or response pending). Limit <3 total.

 // Simpler: keep explicit counters
 logic [1:0] awq, wq, arq;      // buffered not-yet-executed
 logic [2:0] aw_credit, w_credit, ar_credit; // remaining full-credit slots (unretired)
 // accept condition based on unretired credit
 // For AW: unretired = awq + inflight_aw (0 or 1). Keep aw_credit = 3 - unretired.
 // We'll compute ready from unbuffered capacity too (queue max 3).

 assign s_awready = rst_n && (aw_credit != 0) && (awq != 2'd3);
 assign s_wready  = rst_n && (w_credit  != 0) && (wq  != 2'd3);
 assign s_arready = rst_n && (ar_credit != 0) && (arq != 2'd3);

 assign psel = (state==SETUP) || (state==ACCESS);
 assign penable = (state==ACCESS);
 assign pprot = 3'b000;

 // executor consumes: write starts when awq>0 && wq>0
 wire w_eligible = (awq != 0) && (wq != 0);
 wire r_eligible = (arq != 0);

 logic sel_read, sel_write;
 always_comb begin
  sel_read = 0; sel_write = 0;
  if (state==IDLE) begin
   if (r_eligible && (!w_eligible || prefer_read)) sel_read = 1;
   else if (w_eligible) sel_write = 1;
  end
 end

 // Does this edge consume the pending response?
 wire consume_b = bpop;
 wire consume_r = rpop;

 always_ff @(posedge clk) begin
  if (!rst_n) begin
   state <= IDLE;
   aw_wp<=0; aw_rp<=0; w_wp<=0; w_rp<=0; ar_wp<=0; ar_rp<=0;
   awq<=0; wq<=0; arq<=0;
   aw_credit<=3; w_credit<=3; ar_credit<=3;
   prefer_read<=1;
   s_bvalid<=0; s_rvalid<=0; s_bresp<=0; s_rresp<=0; s_rdata<=0;
   paddr<=0; pwdata<=0; pstrb<=0; pwrite<=0;
  end else begin
   // ---- Acceptance pushes ----
   if (apush) begin aq[aw_wp] <= s_awaddr; aw_wp <= aw_wp + 2'd1; end
   if (wpush) begin dq[w_wp] <= s_wdata; sq[w_wp] <= s_wstrb; w_wp <= w_wp + 2'd1; end
   if (rpush) begin rq[ar_wp] <= s_araddr; ar_wp <= ar_wp + 2'd1; end

   // ---- Queue occupancy update ----
   // pops due to executor start happen below; combine carefully with pushes.
   // We handle awq/wq/arq with push and executor-start pop.

   // ---- B/R retire ----
   if (consume_b) begin
    // retire one AW credit (AW was already popped from aq when write started).
    aw_credit <= aw_credit + 3'd1;
    s_bvalid <= 1'b0;
   end
   if (consume_r) begin
    ar_credit <= ar_credit + 3'd1;
    s_rvalid <= 1'b0;
   end

   // ---- Executor / APB FSM ----
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
     // wait for corresponding response handshake; do not select on same edge
     if (bpop || rpop) begin
      s_bvalid <= 1'b0;
      s_rvalid <= 1'b0;
      state <= IDLE;
     end
    end
    default: state <= IDLE;
   endcase

   // ---- Queue occupancy bookkeeping (push on accept, pop on executor start) ----
   // Compute next values combining pushes and sel_start events.
   {
    logic [1:0] awq_next, wq_next, arq_next;
    logic [2:0] awc_next, wc_next, arc_next;
    awq_next = awq; wq_next = wq; arq_next = arq;
    awc_next = aw_credit; wc_next = w_credit; arc_next = ar_credit;
    // If we just added a push this edge, count it. Note: credit was consumed on push.
    if (apush) begin awq_next = awq_next + 2'd1; awc_next = awc_next - 3'd1; end
    if (wpush) begin wq_next  = wq_next  + 2'd1; wc_next  = wc_next  - 3'd1; end
    if (rpush) begin arq_next = arq_next + 2'd1; arc_next = arc_next - 3'd1; end
    // Executor start pops
    if (sel_write) begin awq_next = awq_next - 2'd1; wq_next = wq_next - 2'd1; end
    if (sel_read)  begin arq_next = arq_next - 2'd1; end
    // B/R retire refunds applied here too (override earlier credit add)
    if (consume_b) awc_next = awc_next + 3'd1;
    if (consume_r) arc_next = arc_next + 3'd1;
    // Advance read pointers on executor start
    if (sel_write) begin aw_rp <= aw_rp + 2'd1; w_rp <= w_rp + 2'd1; end
    if (sel_read)  begin ar_rp <= ar_rp + 2'd1; end
    awq <= awq_next; wq <= wq_next; arq <= arq_next;
    aw_credit <= awc_next; w_credit <= wc_next; ar_credit <= arc_next;
   }
  end
 end
endmodule
