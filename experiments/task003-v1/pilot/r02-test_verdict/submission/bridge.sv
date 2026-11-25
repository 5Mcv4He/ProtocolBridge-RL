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
 logic [1:0] aw_head, aw_count;

 // W queue
 logic [31:0] w_q [0:1];
 logic [3:0] w_q_strb [0:1];
 logic [1:0] w_head, w_count;

 // AR queue
 logic [31:0] ar_q [0:1];
 logic [1:0] ar_head, ar_count;

 // executor state
 logic busy;
 logic [1:0] phase; // 1 setup, 2 access
 logic is_write;
 logic [31:0] exec_addr;
 logic [31:0] exec_wdata;
 logic [3:0] exec_strb;

 // response regs
 logic bvalid_r, rvalid_r;
 logic [1:0] bresp_r, rresp_r;
 logic [31:0] rdata_r;

 // which response is currently holding executor (write or read)
 logic pend_write;

 logic pref_read;

 assign s_awready = (aw_count < 2);
 assign s_wready  = (w_count < 2);
 assign s_arready = (ar_count < 2);

 assign s_bvalid = bvalid_r;
 assign s_bresp  = bresp_r;
 assign s_rvalid = rvalid_r;
 assign s_rresp  = rresp_r;
 assign s_rdata  = rdata_r;

 assign psel    = busy && (phase != 0);
 assign penable = busy && (phase == 2);
 assign pwrite  = is_write;
 assign paddr   = exec_addr;
 assign pwdata  = exec_wdata;
 assign pstrb   = is_write ? exec_strb : 4'b0;
 assign pprot   = 3'b000;

 wire write_elig = (aw_count != 0) && (w_count != 0);
 wire read_elig  = (ar_count != 0);
 wire can_start  = !busy && !bvalid_r && !rvalid_r;

 wire sel_write = can_start && write_elig && (read_elig ? !pref_read : 1'b1);
 wire sel_read  = can_start && read_elig && (write_elig ? pref_read : 1'b1);

 wire b_consume = bvalid_r && s_bready;
 wire r_consume = rvalid_r && s_rready;

 integer i;

 always_ff @(posedge clk) begin
  if (!rst_n) begin
   aw_head <= 0; aw_count <= 0;
   w_head <= 0; w_count <= 0;
   ar_head <= 0; ar_count <= 0;
   busy <= 0; phase <= 0; is_write <= 0;
   pref_read <= 1;
   bvalid_r <= 0; rvalid_r <= 0; bresp_r <= 0; rresp_r <= 0; rdata_r <= 0;
   exec_addr <= 0; exec_wdata <= 0; exec_strb <= 0;
   pend_write <= 0;
  end else begin
   // APB executor
   if (busy) begin
    if (phase == 1) begin
     phase <= 2;
    end else if (phase == 2 && pready) begin
     busy <= 0;
     phase <= 0;
     if (is_write) begin
      bresp_r <= pslverr ? 2'b10 : 2'b00;
      bvalid_r <= 1;
      pend_write <= 1;
     end else begin
      rdata_r <= prdata;
      rresp_r <= pslverr ? 2'b10 : 2'b00;
      rvalid_r <= 1;
      pend_write <= 0;
     end
    end
   end

   // response consumption / credit retirement
   if (b_consume) begin
    bvalid_r <= 0;
    aw_head <= aw_head + 1;
    aw_count <= aw_count - 1;
    w_head <= w_head + 1;
    w_count <= w_count - 1;
   end
   if (r_consume) begin
    rvalid_r <= 0;
    ar_head <= ar_head + 1;
    ar_count <= ar_count - 1;
   end

   // start new transaction
   if (can_start) begin
    if (sel_write) begin
     busy <= 1; phase <= 1; is_write <= 1;
     exec_addr <= aw_q[aw_head];
     exec_wdata <= w_q[w_head];
     exec_strb <= w_q_strb[w_head];
     pref_read <= 0;
    end else if (sel_read) begin
     busy <= 1; phase <= 1; is_write <= 0;
     exec_addr <= ar_q[ar_head];
     pref_read <= 1;
    end
   end

   // accept AW
   if (s_awvalid && s_awready) begin
    aw_q[aw_count] <= s_awaddr;
    aw_count <= aw_count + 1;
   end
   // accept W
   if (s_wvalid && s_wready) begin
    w_q[w_count] <= s_wdata;
    w_q_strb[w_count] <= s_wstrb;
    w_count <= w_count + 1;
   end
   // accept AR
   if (s_arvalid && s_arready) begin
    ar_q[ar_count] <= s_araddr;
    ar_count <= ar_count + 1;
   end
  end
 end

endmodule