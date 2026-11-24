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

 typedef enum logic [2:0] {
   IDLE,
   SETUP,
   ACCESS,
   RESP
 } state_t;

 state_t state;

 // captured request
 logic [31:0] req_addr;
 logic [3:0]  req_strb;
 logic [31:0] req_wdata;
 logic        req_write;

 // buffered response
 logic [31:0] resp_rdata;
 logic [1:0]  resp_resp;

 // pending accepted halves
 logic        aw_pending;
 logic [31:0] aw_addr;
 logic        w_pending;
 logic [31:0] w_data;
 logic [3:0]  w_strb;

 // ------------------------------------------------------------
 // Ready outputs
 // ------------------------------------------------------------
 assign s_awready = (state == IDLE) && !aw_pending;
 assign s_wready  = (state == IDLE) && !w_pending;
 // AR accepted only when idle with no partial write halves pending
 assign s_arready = (state == IDLE) && !aw_pending && !w_pending;

 // ------------------------------------------------------------
 // AXI response outputs (buffered)
 // ------------------------------------------------------------
 assign s_bvalid = (state == RESP) && req_write;
 assign s_bresp  = resp_resp;

 assign s_rvalid = (state == RESP) && !req_write;
 assign s_rdata  = resp_rdata;
 assign s_rresp  = resp_resp;

 // ------------------------------------------------------------
 // APB outputs
 // ------------------------------------------------------------
 assign paddr   = req_addr;
 assign pwdata  = req_wdata;
 assign pstrb   = req_write ? req_strb : 4'b0000;
 assign pprot   = 3'b000;
 assign pwrite  = req_write;
 assign psel    = (state == SETUP) || (state == ACCESS);
 assign penable = (state == ACCESS);

 // ------------------------------------------------------------
 // Sequential
 // ------------------------------------------------------------
 always_ff @(posedge clk) begin
   if (!rst_n) begin
     state      <= IDLE;
     aw_pending <= 1'b0;
     aw_addr    <= 32'd0;
     w_pending  <= 1'b0;
     w_data     <= 32'd0;
     w_strb     <= 4'd0;
     req_addr   <= 32'd0;
     req_wdata  <= 32'd0;
     req_strb   <= 4'd0;
     req_write  <= 1'b0;
     resp_rdata <= 32'd0;
     resp_resp  <= 2'b00;
   end else begin
     case (state)
       IDLE: begin
         // Capture write halves
         if (s_awvalid && s_awready) begin
           aw_pending <= 1'b1;
           aw_addr    <= s_awaddr;
         end
         if (s_wvalid && s_wready) begin
           w_pending <= 1'b1;
           w_data    <= s_wdata;
           w_strb    <= s_wstrb;
         end

         // Decide next request
         if (s_arvalid && s_arready) begin
           req_addr  <= s_araddr;
           req_write <= 1'b0;
           req_wdata <= 32'd0;
           req_strb  <= 4'd0;
           state     <= SETUP;
         end else if ((aw_pending && w_pending) ||
                      (aw_pending && s_wvalid && s_wready) ||
                      (w_pending  && s_awvalid && s_awready)) begin
           // both halves available
           req_addr  <= s_awvalid && s_awready ? s_awaddr : aw_addr;
           req_wdata <= s_wvalid && s_wready  ? s_wdata  : w_data;
           req_strb  <= s_wvalid && s_wready  ? s_wstrb  : w_strb;
           req_write <= 1'b1;
           aw_pending <= 1'b0;
           w_pending  <= 1'b0;
           state      <= SETUP;
         end
       end

       SETUP: begin
         state <= ACCESS;
       end

       ACCESS: begin
         if (pready) begin
           resp_rdata <= prdata;
           resp_resp  <= pslverr ? 2'b10 : 2'b00;
           state      <= RESP;
         end
       end

       RESP: begin
         if (req_write ? s_bready : s_rready) begin
           state <= IDLE;
         end
       end

       default: state <= IDLE;
     endcase
   end
 end

endmodule
