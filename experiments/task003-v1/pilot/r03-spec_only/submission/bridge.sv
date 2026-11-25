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

 // AW queue
 logic [31:0] aw_q [0:1];
 logic [1:0] aw_cnt;
 // W queue
 logic [31:0] w_q [0:1];
 logic [3:0] wstrb_q [0:1];
 logic [1:0] w_cnt;
 // AR queue
 logic [31:0] ar_q [0:1];
 logic [1:0] ar_cnt;

 logic pref; // 0=READ, 1=WRITE

 logic bvalid_r;
 logic [1:0] bresp_r;
 logic rvalid_r;
 logic [31:0] rdata_r;
 logic [1:0] rresp_r;

 logic [1:0] apb_state; // 0 idle, 1 setup, 2 access
 logic [31:0] addr_r;
 logic [31:0] wdata_r;
 logic [3:0] pstrb_r;
 logic dir_w;

 wire busy = (apb_state != 0) || bvalid_r || rvalid_r;

 wire aw_full = (aw_cnt==2'd2);
 wire w_full  = (w_cnt==2'd2);
 wire ar_full = (ar_cnt==2'd2);

 assign s_awready = rst_n && !aw_full;
 assign s_wready  = rst_n && !w_full;
 assign s_arready = rst_n && !ar_full;

 assign pprot = 3'b000;

 wire aw_accept = s_awvalid && s_awready;
 wire w_accept  = s_wvalid && s_wready;
 wire ar_accept = s_arvalid && s_arready;

 wire b_consume = bvalid_r && s_bready;
 wire r_consume = rvalid_r && s_rready;

 wire write_elig = (aw_cnt!=2'd0) && (w_cnt!=2'd0);
 wire read_elig  = (ar_cnt!=2'd0);

 wire sel_write = !busy && write_elig && (read_elig ? pref : 1'b1);
 wire sel_read  = !busy && read_elig && (write_elig ? !pref : 1'b1);
 wire do_sel = sel_write || sel_read;

 always_ff @(posedge clk) begin
  if (!rst_n) begin
   aw_cnt <= 0;
   w_cnt <= 0;
   ar_cnt <= 0;
   pref <= 1'b0;
   bvalid_r <= 0;
   bresp_r <= 0;
   rvalid_r <= 0;
   rdata_r <= 0;
   rresp_r <= 0;
   apb_state <= 0;
   psel <= 0;
   penable <= 0;
   pwrite <= 0;
   paddr <= 0;
   pwdata <= 0;
   pstrb <= 0;
   addr_r <= 0;
   wdata_r <= 0;
   pstrb_r <= 0;
   dir_w <= 0;
  end else begin
   // Response consumption retires credits
   if (b_consume) begin
    if (aw_cnt!=0) begin aw_q[0] <= aw_q[1]; aw_cnt <= aw_cnt-1; end
    if (w_cnt!=0)  begin w_q[0] <= w_q[1]; wstrb_q[0] <= wstrb_q[1]; w_cnt <= w_cnt-1; end
    bvalid_r <= 0;
   end
   if (r_consume) begin
    if (ar_cnt!=0) begin ar_q[0] <= ar_q[1]; ar_cnt <= ar_cnt-1; end
    rvalid_r <= 0;
   end

   // APB state machine
   if (apb_state==2'd0) begin
    psel <= 0; penable <= 0;
    if (do_sel && !bvalid_r && !rvalid_r) begin
     if (sel_write) begin
      addr_r <= aw_q[0];
      wdata_r <= w_q[0];
      pstrb_r <= wstrb_q[0];
      pwrite <= 1'b1;
      dir_w <= 1'b1;
      pref <= 1'b0;
     end else begin
      addr_r <= ar_q[0];
      wdata_r <= 0;
      pstrb_r <= 0;
      pwrite <= 1'b0;
      dir_w <= 1'b0;
      pref <= 1'b1;
     end
     paddr <= addr_r;
     pwdata <= wdata_r;
     pstrb <= pstrb_r;
     psel <= 1;
     penable <= 0;
     apb_state <= 2'd1;
    end
   end else if (apb_state==2'd1) begin
    psel <= 1;
    penable <= 1;
    if (pready) begin
     apb_state <= 2'd0;
     psel <= 0;
     penable <= 0;
     if (dir_w) begin
      bvalid_r <= 1;
      bresp_r <= pslverr ? 2'b10 : 2'b00;
     end else begin
      rvalid_r <= 1;
      rdata_r <= prdata;
      rresp_r <= pslverr ? 2'b10 : 2'b00;
     end
    end
   end

   // Queue enqueues (append)
   if (aw_accept) begin
    aw_q[aw_cnt] <= s_awaddr;
    aw_cnt <= aw_cnt + 1;
   end
   if (w_accept) begin
    w_q[w_cnt] <= s_wdata;
    wstrb_q[w_cnt] <= s_wstrb;
    w_cnt <= w_cnt + 1;
   end
   if (ar_accept) begin
    ar_q[ar_cnt] <= s_araddr;
    ar_cnt <= ar_cnt + 1;
   end
  end
 end

 assign s_bvalid = bvalid_r;
 assign s_bresp = bresp_r;
 assign s_rvalid = rvalid_r;
 assign s_rdata = rdata_r;
 assign s_rresp = rresp_r;

endmodule
