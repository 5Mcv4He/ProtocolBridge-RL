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

 // Write half buffers
 logic aw_full, w_full;
 logic [31:0] aw_addr_buf, w_data_buf;
 logic [3:0] w_strb_buf;

 // APB phase tracking
 logic apb_active;   // 0 = idle, 1 = setup, 2 = access

 // Response tracking
 logic b_pending;
 logic [1:0] bresp_r;
 logic r_pending;
 logic [31:0] rdata_r;
 logic [1:0] rresp_r;

 // Direction chosen when transaction launches
 logic cur_write;
 logic has_write_trans; // both halves accepted, waiting to launch
 logic has_read_trans;
 logic [31:0] ar_addr_buf;

 // Latched APB outputs for current transfer
 logic [31:0] apb_addr;
 logic [31:0] apb_wdata;
 logic [3:0] apb_strb;
 logic apb_write;

 assign s_awready = rst_n && !aw_full && !b_pending && !has_write_trans && !has_read_trans && !apb_active;
 assign s_wready  = rst_n && !w_full  && !b_pending && !has_write_trans && !has_read_trans && !apb_active;
 assign s_arready = rst_n && !b_pending && !r_pending && !has_write_trans && !has_read_trans && !apb_active
                    && !aw_full && !w_full && !s_awvalid && !s_wvalid;

 assign s_bvalid = b_pending;
 assign s_bresp  = bresp_r;
 assign s_rvalid = r_pending;
 assign s_rdata  = rdata_r;
 assign s_rresp  = rresp_r;

 assign psel    = (apb_active != 2'd0);
 assign penable = (apb_active == 2'd2);
 assign pwrite  = apb_write;
 assign paddr   = apb_addr;
 assign pwdata  = apb_wdata;
 assign pstrb   = apb_strb;
 assign pprot   = 3'b000;

 always_ff @(posedge clk) begin
  if (!rst_n) begin
   aw_full <= 1'b0; w_full <= 1'b0;
   aw_addr_buf <= 32'b0; w_data_buf <= 32'b0; w_strb_buf <= 4'b0;
   apb_active <= 2'd0;
   b_pending <= 1'b0; bresp_r <= 2'b0;
   r_pending <= 1'b0; rdata_r <= 32'b0; rresp_r <= 2'b0;
   cur_write <= 1'b0;
   has_write_trans <= 1'b0; has_read_trans <= 1'b0;
   ar_addr_buf <= 32'b0;
   apb_addr <= 32'b0; apb_wdata <= 32'b0; apb_strb <= 4'b0; apb_write <= 1'b0;
  end else begin
   // Capture write halves
   if (s_awvalid && s_awready) begin
    aw_full <= 1'b1;
    aw_addr_buf <= s_awaddr;
   end
   if (s_wvalid && s_wready) begin
    w_full <= 1'b1;
    w_data_buf <= s_wdata;
    w_strb_buf <= s_wstrb;
   end

   // Capture read address
   if (s_arvalid && s_arready) begin
    has_read_trans <= 1'b1;
    ar_addr_buf <= s_araddr;
   end

   // Both write halves present -> launch write transaction
   if (!has_write_trans && aw_full && w_full && !apb_active && !b_pending) begin
    has_write_trans <= 1'b1;
   end

   // Launch APB when armed and idle
   if (apb_active == 2'd0) begin
    if (has_write_trans) begin
     apb_active <= 2'd1;
     apb_write <= 1'b1;
     apb_addr <= aw_addr_buf;
     apb_wdata <= w_data_buf;
     apb_strb <= w_strb_buf;
     cur_write <= 1'b1;
     // free halves
     aw_full <= 1'b0; w_full <= 1'b0;
     has_write_trans <= 1'b0;
    end else if (has_read_trans) begin
     apb_active <= 2'd1;
     apb_write <= 1'b0;
     apb_addr <= ar_addr_buf;
     apb_wdata <= 32'b0;
     apb_strb <= 4'b0;
     cur_write <= 1'b0;
     has_read_trans <= 1'b0;
    end
   end else if (apb_active == 2'd1) begin
    apb_active <= 2'd2;
   end else begin
    if (pready) begin
     apb_active <= 2'd0;
     if (cur_write) begin
      b_pending <= 1'b1;
      bresp_r <= pslverr ? 2'b10 : 2'b00;
     end else begin
      r_pending <= 1'b1;
      rdata_r <= prdata;
      rresp_r <= pslverr ? 2'b10 : 2'b00;
     end
    end
   end

   // Response handshakes free the response slot
   if (b_pending && s_bready) begin
    b_pending <= 1'b0;
   end
   if (r_pending && s_rready) begin
    r_pending <= 1'b0;
   end
  end
 end

endmodule
