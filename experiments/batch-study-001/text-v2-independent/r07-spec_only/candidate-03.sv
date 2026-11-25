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
 logic aw_have, w_have;
 logic [31:0] awaddr_buf, wdata_buf;
 logic [3:0] wstrb_buf;

 // Read request buffer (accepted AR)
 logic ar_have;
 logic [31:0] araddr_buf;

 // APB FSM
 localparam IDLE  = 2'd0;
 localparam SETUP = 2'd1;
 localparam ACCESS= 2'd2;
 logic [1:0] state;

 logic is_write; // 1 = write transaction in progress

 // Response pending registers
 logic b_pending;
 logic [1:0] bresp_r;
 logic r_pending;
 logic [31:0] rdata_r;
 logic [1:0] rresp_r;

 // Handshakes
 assign s_awready = !aw_have && !b_pending && !r_pending && (state == IDLE) && !is_write_busy();
 assign s_wready  = !w_have  && !b_pending && !r_pending && (state == IDLE) && !is_write_busy();
 assign s_arready = !ar_have && !b_pending && !r_pending && (state == IDLE) && !aw_have && !w_have && !is_write_busy();

 function automatic logic is_write_busy();
   return (state != IDLE) && is_write;
 endfunction

 assign s_bvalid = b_pending;
 assign s_bresp  = bresp_r;
 assign s_rvalid = r_pending;
 assign s_rdata  = rdata_r;
 assign s_rresp  = rresp_r;

 assign psel    = (state == SETUP) || (state == ACCESS);
 assign penable = (state == ACCESS);
 assign pwrite  = is_write;
 assign pprot   = 3'b000;

 assign paddr  = is_write ? awaddr_buf : araddr_buf;
 assign pwdata = is_write ? wdata_buf : 32'b0;
 assign pstrb  = is_write ? wstrb_buf : 4'b0;

 always_ff @(posedge clk) begin
   if (!rst_n) begin
     aw_have <= 1'b0; w_have <= 1'b0; ar_have <= 1'b0;
     awaddr_buf <= 32'b0; wdata_buf <= 32'b0; wstrb_buf <= 4'b0;
     araddr_buf <= 32'b0;
     state <= IDLE;
     is_write <= 1'b0;
     b_pending <= 1'b0; bresp_r <= 2'b00;
     r_pending <= 1'b0; rdata_r <= 32'b0; rresp_r <= 2'b00;
   end else begin
     // Clear responses on handshake
     if (b_pending && s_bready) b_pending <= 1'b0;
     if (r_pending && s_rready) r_pending <= 1'b0;

     // Accept request halves when idle
     if (s_awready && s_awvalid) begin
       aw_have <= 1'b1;
       awaddr_buf <= s_awaddr;
     end
     if (s_wready && s_wvalid) begin
       w_have <= 1'b1;
       wdata_buf <= s_wdata;
       wstrb_buf <= s_wstrb;
     end
     if (s_arready && s_arvalid) begin
       ar_have <= 1'b1;
       araddr_buf <= s_araddr;
     end

     case (state)
       IDLE: begin
         if (aw_have && w_have) begin
           is_write <= 1'b1;
           state <= SETUP;
           // consume write halves into APB regs (kept in awaddr_buf/wdata_buf)
           aw_have <= 1'b0;
           w_have <= 1'b0;
         end else if (ar_have) begin
           is_write <= 1'b0;
           state <= SETUP;
           ar_have <= 1'b0;
         end
       end
       SETUP: begin
         state <= ACCESS;
       end
       ACCESS: begin
         if (pready) begin
           state <= IDLE;
           if (is_write) begin
             b_pending <= 1'b1;
             bresp_r <= pslverr ? 2'b10 : 2'b00;
           end else begin
             r_pending <= 1'b1;
             rdata_r <= prdata;
             rresp_r <= pslverr ? 2'b10 : 2'b00;
           end
         end
       end
       default: state <= IDLE;
     endcase

     // Prevent accepting new halves if response set this cycle would conflict:
     // handled by ready conditions checking b_pending/r_pending; but b_pending
     // is only set next cycle after APB completion, and state returns IDLE same
     // time so no conflict since ready requires IDLE and !pending registers
     // from previous cycle. Accepting in the completion cycle is impossible
     // because state != IDLE during ACCESS.
   end
 end

endmodule
