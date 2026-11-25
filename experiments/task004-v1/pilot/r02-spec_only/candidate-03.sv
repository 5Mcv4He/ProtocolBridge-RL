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
 localparam S_IDLE=2'd0, S_SETUP=2'd1, S_ACCESS=2'd2;

 // AW queue (capacity 3). Credits held until B handshake.
 logic [31:0] aw_addr [0:2];
 logic aw_valid [0:2];
 logic [1:0] aw_wp, aw_rp; // wp = next free slot, rp = oldest
 logic [1:0] aw_cnt;

 // W queue
 logic [31:0] w_data [0:2];
 logic [3:0] w_strb [0:2];
 logic w_valid [0:2];
 logic [1:0] w_wp, w_rp;
 logic [1:0] w_cnt;

 // AR queue
 logic [31:0] ar_addr [0:2];
 logic ar_valid [0:2];
 logic [1:0] ar_wp, ar_rp;
 logic [1:0] ar_cnt;

 // B response queue
 logic [1:0] b_resp [0:2];
 logic b_vld [0:2];
 logic [1:0] b_wp, b_rp;
 logic [1:0] b_cnt;

 // R response queue
 logic [31:0] r_data [0:2];
 logic [1:0] r_resp [0:2];
 logic r_vld [0:2];
 logic [1:0] r_wp, r_rp;
 logic [1:0] r_cnt;

 // executor
 logic [1:0] state;
 logic pref; // 0 = READ preferred
 // active transaction info
 logic act_pwrite;
 logic [31:0] act_addr;
 logic [31:0] act_wdata;
 logic [3:0] act_strb;

 // helper signals
 logic aw_avail, w_avail, ar_avail;
 logic sel_write, sel_read;
 logic do_grant;

 assign aw_avail = aw_cnt != 2'd0;
 assign w_avail  = w_cnt  != 2'd0;
 assign ar_avail = ar_cnt != 2'd0;

 assign sel_write = aw_avail && w_avail;
 assign sel_read  = ar_avail;

 assign do_grant = (state==S_IDLE) && (
                     (sel_write && sel_read) ? (pref==1'b1) :  // pref==1 -> WRITE preferred
                     sel_write ? 1'b1 :
                     sel_read  ? 1'b0 : 1'b0);

 // Ready outputs: accept if channel not full (and not in reset)
 assign s_awready = rst_n && (aw_cnt != 2'd3);
 assign s_wready  = rst_n && (w_cnt  != 2'd3);
 assign s_arready = rst_n && (ar_cnt != 2'd3);

 // Response valid = queue head has data
 assign s_bvalid = (b_cnt != 2'd0);
 assign s_bresp  = b_resp[b_rp];
 assign s_rvalid = (r_cnt != 2'd0);
 assign s_rdata  = r_data[r_rp];
 assign s_rresp  = r_resp[r_rp];

 // APB outputs driven from registered state
 assign psel   = (state==S_SETUP) || (state==S_ACCESS);
 assign penable = (state==S_ACCESS);
 assign pwrite = act_pwrite;
 assign paddr  = act_addr;
 assign pwdata = act_wdata;
 assign pstrb  = act_pwrite ? act_strb : 4'b0;
 assign pprot  = 3'b0;

 integer i;

 always_ff @(posedge clk) begin
  if (!rst_n) begin
   state <= S_IDLE;
   pref <= 1'b0;
   aw_wp <= 2'd0; aw_rp <= 2'd0; aw_cnt <= 2'd0;
   w_wp  <= 2'd0; w_rp  <= 2'd0; w_cnt  <= 2'd0;
   ar_wp <= 2'd0; ar_rp <= 2'd0; ar_cnt <= 2'd0;
   b_wp  <= 2'd0; b_rp  <= 2'd0; b_cnt  <= 2'd0;
   r_wp  <= 2'd0; r_rp  <= 2'd0; r_cnt  <= 2'd0;
   act_pwrite <= 1'b0;
   act_addr <= 32'd0;
   act_wdata <= 32'd0;
   act_strb <= 4'd0;
   for (i=0;i<3;i=i+1) begin
    aw_valid[i] <= 1'b0;
    w_valid[i]  <= 1'b0;
    ar_valid[i] <= 1'b0;
    b_vld[i]    <= 1'b0;
    r_vld[i]    <= 1'b0;
   end
  end else begin
   // ---- APB executor state machine ----
   case (state)
    S_IDLE: begin
     if (do_grant) begin
      if (sel_write && !sel_read) begin
       // write only
       act_pwrite <= 1'b1;
       act_addr   <= aw_addr[aw_rp];
       act_wdata  <= w_data[w_rp];
       act_strb   <= w_strb[w_rp];
       aw_valid[aw_rp] <= 1'b0;
       w_valid[w_rp]   <= 1'b0;
       aw_rp <= aw_rp + 2'd1;
       w_rp  <= w_rp  + 2'd1;
       aw_cnt <= aw_cnt - 2'd1;
       w_cnt  <= w_cnt  - 2'd1;
       pref <= 1'b0; // flip to READ preferred
      end else if (!sel_write && sel_read) begin
       act_pwrite <= 1'b0;
       act_addr   <= ar_addr[ar_rp];
       act_wdata  <= 32'd0;
       act_strb   <= 4'd0;
       ar_valid[ar_rp] <= 1'b0;
       ar_rp <= ar_rp + 2'd1;
       ar_cnt <= ar_cnt - 2'd1;
       pref <= 1'b1; // flip to WRITE preferred
      end else begin
       // both eligible, pref decides
       if (pref==1'b1) begin
        // grant WRITE
        act_pwrite <= 1'b1;
        act_addr   <= aw_addr[aw_rp];
        act_wdata  <= w_data[w_rp];
        act_strb   <= w_strb[w_rp];
        aw_valid[aw_rp] <= 1'b0;
        w_valid[w_rp]   <= 1'b0;
        aw_rp <= aw_rp + 2'd1;
        w_rp  <= w_rp  + 2'd1;
        aw_cnt <= aw_cnt - 2'd1;
        w_cnt  <= w_cnt  - 2'd1;
        pref <= 1'b0;
       end else begin
        act_pwrite <= 1'b0;
        act_addr   <= ar_addr[ar_rp];
        act_wdata  <= 32'd0;
        act_strb   <= 4'd0;
        ar_valid[ar_rp] <= 1'b0;
        ar_rp <= ar_rp + 2'd1;
        ar_cnt <= ar_cnt - 2'd1;
        pref <= 1'b1;
       end
      end
      state <= S_SETUP;
     end
    end
    S_SETUP: begin
     state <= S_ACCESS;
    end
    S_ACCESS: begin
     if (pready) begin
      // Complete: enqueue response
      if (act_pwrite) begin
       b_resp[b_wp] <= pslverr ? 2'b10 : 2'b00;
       b_vld[b_wp]  <= 1'b1;
       b_wp <= b_wp + 2'd1;
      end else begin
       r_data[r_wp] <= prdata;
       r_resp[r_wp] <= pslverr ? 2'b10 : 2'b00;
       r_vld[r_wp]  <= 1'b1;
       r_wp <= r_wp + 2'd1;
      end
      state <= S_IDLE;
     end
    end
    default: state <= S_IDLE;
   endcase

   // ---- B response dequeue ----
   if (b_cnt != 2'd0 && s_bready) begin
    b_vld[b_rp] <= 1'b0;
    b_rp <= b_rp + 2'd1;
   end

   // ---- R response dequeue ----
   if (r_cnt != 2'd0 && s_rready) begin
    r_vld[r_rp] <= 1'b0;
    r_rp <= r_rp + 2'd1;
   end

   // ---- counts update ----
   // AW
   if (s_awvalid && s_awready) begin
    aw_addr[aw_wp] <= s_awaddr;
    aw_valid[aw_wp] <= 1'b1;
    aw_wp <= aw_wp + 2'd1;
   end
   // W
   if (s_wvalid && s_wready) begin
    w_data[w_wp] <= s_wdata;
    w_strb[w_wp] <= s_wstrb;
    w_valid[w_wp] <= 1'b1;
    w_wp <= w_wp + 2'd1;
   end
   // AR
   if (s_arvalid && s_arready) begin
    ar_addr[ar_wp] <= s_araddr;
    ar_valid[ar_wp] <= 1'b1;
    ar_wp <= ar_wp + 2'd1;
   end

   // count updates (accept + grant + dequeue)
   // AW: accept +1, grant -1
   aw_cnt <= aw_cnt
           + ((s_awvalid && s_awready) ? 2'd1 : 2'd0)
           + (((state==S_IDLE) && do_grant && (sel_write && !sel_read || (sel_write && sel_read && pref==1'b1))) ? 2'd3 : 2'd0);
   w_cnt  <= w_cnt
           + ((s_wvalid && s_wready) ? 2'd1 : 2'd0)
           + (((state==S_IDLE) && do_grant && (sel_write && !sel_read || (sel_write && sel_read && pref==1'b1))) ? 2'd3 : 2'd0);
   ar_cnt <= ar_cnt
           + ((s_arvalid && s_arready) ? 2'd1 : 2'd0)
           + (((state==S_IDLE) && do_grant && (!sel_write && sel_read || (sel_write && sel_read && pref==1'b0))) ? 2'd3 : 2'd0);

   // B count: enqueue on APB completion, dequeue on handshake
   begin
    logic b_enq, b_deq;
    b_enq = (state==S_ACCESS) && pready && act_pwrite;
    b_deq = (b_cnt != 2'd0) && s_bready;
    if (b_enq && !b_deq) b_cnt <= b_cnt + 2'd1;
    else if (!b_enq && b_deq) b_cnt <= b_cnt + 2'd3; // -1
    else b_cnt <= b_cnt;
   end

   // R count
   begin
    logic r_enq, r_deq;
    r_enq = (state==S_ACCESS) && pready && !act_pwrite;
    r_deq = (r_cnt != 2'd0) && s_rready;
    if (r_enq && !r_deq) r_cnt <= r_cnt + 2'd1;
    else if (!r_enq && r_deq) r_cnt <= r_cnt + 2'd3; // -1
    else r_cnt <= r_cnt;
   end
  end
 end
endmodule
