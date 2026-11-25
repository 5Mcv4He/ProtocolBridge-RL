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

 // Write-half buffers
 logic aw_buf_valid, w_buf_valid;
 logic [31:0] aw_buf_addr, w_buf_data;
 logic [3:0]  w_buf_strb;

 // Read request buffer
 logic ar_buf_valid;
 logic [31:0] ar_buf_addr;

 // Pending AXI response
 logic b_pend, b_is_err;
 logic r_pend, r_is_err;
 logic [31:0] r_data;

 // APB state
 logic apb_active;   // a transfer is in progress (setup or access)
 logic apb_setup;    // in setup cycle (next cycle goes to access)
 logic apb_is_write;
 logic [31:0] apb_addr, apb_wdata;
 logic [3:0]  apb_strb;

 // Can accept new AW/W/AR only when nothing is going on
 wire idle = ~aw_buf_valid & ~w_buf_valid & ~ar_buf_valid &
             ~b_pend & ~r_pend & ~apb_active;

 assign s_awready = idle;
 assign s_wready  = idle;
 assign s_arready = idle;

 assign pprot = 3'b000;

 assign s_bvalid = b_pend;
 assign s_bresp  = b_is_err ? 2'b10 : 2'b00;
 assign s_rvalid = r_pend;
 assign s_rdata  = r_data;
 assign s_rresp  = r_is_err ? 2'b10 : 2'b00;

 assign psel    = apb_active;
 assign penable = apb_active & ~apb_setup;
 assign pwrite  = apb_is_write;
 assign paddr   = apb_addr;
 assign pwdata  = apb_wdata;
 assign pstrb   = apb_strb;

 wire write_ready = aw_buf_valid & w_buf_valid;

 always_ff @(posedge clk) begin
  if (!rst_n) begin
   aw_buf_valid <= 1'b0;
   w_buf_valid  <= 1'b0;
   ar_buf_valid <= 1'b0;
   aw_buf_addr  <= 32'b0;
   w_buf_data   <= 32'b0;
   w_buf_strb   <= 4'b0;
   ar_buf_addr  <= 32'b0;
   b_pend       <= 1'b0;
   b_is_err     <= 1'b0;
   r_pend       <= 1'b0;
   r_is_err     <= 1'b0;
   r_data       <= 32'b0;
   apb_active   <= 1'b0;
   apb_setup    <= 1'b0;
   apb_is_write <= 1'b0;
   apb_addr     <= 32'b0;
   apb_wdata    <= 32'b0;
   apb_strb     <= 4'b0;
  end else begin
   // Capture AXI request halves when idle
   if (idle) begin
    if (s_awvalid) begin
     aw_buf_valid <= 1'b1;
     aw_buf_addr  <= s_awaddr;
    end
    if (s_wvalid) begin
     w_buf_valid <= 1'b1;
     w_buf_data  <= s_wdata;
     w_buf_strb  <= s_wstrb;
    end
    if (s_arvalid) begin
     ar_buf_valid <= 1'b1;
     ar_buf_addr  <= s_araddr;
    end
   end

   // Handle AXI responses
   if (b_pend && s_bready) begin
    b_pend <= 1'b0;
   end
   if (r_pend && s_rready) begin
    r_pend <= 1'b0;
   end

   // APB engine
   if (!apb_active) begin
    // Start a write transfer if both halves buffered; reads cannot start while write halves buffered
    if (write_ready) begin
     apb_active   <= 1'b1;
     apb_setup    <= 1'b1;
     apb_is_write <= 1'b1;
     apb_addr     <= aw_buf_addr;
     apb_wdata    <= w_buf_data;
     apb_strb     <= w_buf_strb;
     aw_buf_valid <= 1'b0;
     w_buf_valid  <= 1'b0;
    end else if (ar_buf_valid) begin
     apb_active   <= 1'b1;
     apb_setup    <= 1'b1;
     apb_is_write <= 1'b0;
     apb_addr     <= ar_buf_addr;
     apb_wdata    <= 32'b0;
     apb_strb     <= 4'b0;
     ar_buf_valid <= 1'b0;
    end
   end else if (apb_setup) begin
    apb_setup <= 1'b0;
   end else begin
    // Access phase, waiting for PREADY
    if (pready) begin
     apb_active <= 1'b0;
     apb_setup  <= 1'b0;
     if (apb_is_write) begin
      b_pend   <= 1'b1;
      b_is_err <= pslverr;
     end else begin
      r_pend   <= 1'b1;
      r_is_err <= pslverr;
      r_data   <= prdata;
     end
    end
   end

   // Reset clears cross-effects: if reset handled above via if(!rst_n) block.
   // Ensure response cleared if it was just asserted same cycle as reset in next...
  end
 end

endmodule
