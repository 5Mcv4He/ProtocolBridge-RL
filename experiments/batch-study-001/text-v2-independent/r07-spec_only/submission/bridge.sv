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

 // Data latched into APB shaper
 logic [31:0] aaddr;
 logic [31:0] awdata;
 logic [3:0] awstrb;

 // Response pending registers
 logic b_pending;
 logic [1:0] bresp_r;
 logic r_pending;
 logic [31:0] rdata_r;
 logic [1:0] rresp_r;

 wire idle_in = (state == IDLE) && !b_pending && !r_pending;

 assign s_awready = idle_in && !aw_have && !w_have && !ar_have;
 assign s_wready  = idle_in && !aw_have && !w_have && !ar_have;
 assign s_arready = idle_in && !aw_have && !w_have && !ar_have;

 assign s_bvalid = b_pending;
 assign s_bresp  = bresp_r;
 assign s_rvalid = r_pending;
 assign s_rdata  = rdata_r;
 assign s_rresp  = rresp_r;

 assign psel    = (state == SETUP) || (state == ACCESS);
 assign penable = (state == ACCESS);
 assign pwrite  = is_write;
 assign pprot   = 3'b000;

 assign paddr  = aaddr;
 assign pwdata = awdata;
 assign pstrb  = awstrb;

 always_ff @(posedge clk) begin
   if (!rst_n) begin
     aw_have <= 1'b0; w_have <= 1'b0; ar_have <= 1'b0;
     awaddr_buf <= 32'b0; wdata_buf <= 32'b0; wstrb_buf <= 4'b0;
     araddr_buf <= 32'b0;
     aaddr <= 32'b0; awdata <= 32'b0; awstrb <= 4'b0;
     state <= IDLE;
     is_write <= 1'b0;
     b_pending <= 1'b0; bresp_r <= 2'b00;
     r_pending <= 1'b0; rdata_r <= 32'b0; rresp_r <= 2'b00;
   end else begin
     if (b_pending && s_bready) b_pending <= 1'b0;
     if (r_pending && s_rready) r_pending <= 1'b0;

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
           aaddr  <= awaddr_buf;
           awdata <= wdata_buf;
           awstrb <= wstrb_buf;
           aw_have <= 1'b0;
           w_have <= 1'b0;
           state <= SETUP;
         end else if (ar_have) begin
           is_write <= 1'b0;
           aaddr  <= araddr_buf;
           awdata <= 32'b0;
           awstrb <= 4'b0;
           ar_have <= 1'b0;
           state <= SETUP;
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
   end
 end

endmodule
