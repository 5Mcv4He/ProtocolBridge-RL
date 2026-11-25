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
   APB_SETUP,
   APB_ACCESS,
   RESP_WR,
   RESP_RD
 } state_t;

 state_t state, next_state;

 // buffered write halves
 logic have_aw, have_w, have_ar;
 logic [31:0] awaddr_buf, wdata_buf;
 logic [3:0] wstrb_buf;
 logic [31:0] araddr_buf;

 // response payload registers
 logic [1:0] bresp_r, rresp_r;
 logic [31:0] rdata_r;

 // APB control registers
 logic [31:0] paddr_r, pwdata_r;
 logic [3:0] pstrb_r;
 logic pwrite_r;

 logic apb_is_write;

 assign s_awready = rst_n && (state == IDLE) && !have_aw;
 assign s_wready  = rst_n && (state == IDLE) && !have_w;
 assign s_arready = rst_n && (state == IDLE) && !have_ar;

 assign s_bvalid = (state == RESP_WR);
 assign s_bresp  = bresp_r;
 assign s_rvalid = (state == RESP_RD);
 assign s_rdata  = rdata_r;
 assign s_rresp  = rresp_r;

 assign psel    = (state == APB_SETUP) || (state == APB_ACCESS);
 assign penable = (state == APB_ACCESS);
 assign pwrite  = pwrite_r;
 assign paddr   = paddr_r;
 assign pwdata  = pwdata_r;
 assign pstrb   = pstrb_r;
 assign pprot   = 3'b000;

 always_comb begin
   next_state = state;
   case (state)
     IDLE: begin
       if (have_ar) begin
         next_state = APB_SETUP;
       end else if (have_aw && have_w) begin
         next_state = APB_SETUP;
       end else begin
         next_state = IDLE;
       end
     end
     APB_SETUP: begin
       next_state = APB_ACCESS;
     end
     APB_ACCESS: begin
       if (pready) begin
         next_state = apb_is_write ? RESP_WR : RESP_RD;
       end else begin
         next_state = APB_ACCESS;
       end
     end
     RESP_WR: begin
       next_state = s_bready ? IDLE : RESP_WR;
     end
     RESP_RD: begin
       next_state = s_rready ? IDLE : RESP_RD;
     end
     default: next_state = IDLE;
   endcase
 end

 always_ff @(posedge clk) begin
   if (!rst_n) begin
     state        <= IDLE;
     have_aw      <= 1'b0;
     have_w       <= 1'b0;
     have_ar      <= 1'b0;
     awaddr_buf   <= 32'b0;
     wdata_buf    <= 32'b0;
     wstrb_buf    <= 4'b0;
     araddr_buf   <= 32'b0;
     bresp_r      <= 2'b00;
     rresp_r      <= 2'b00;
     rdata_r      <= 32'b0;
     paddr_r      <= 32'b0;
     pwdata_r     <= 32'b0;
     pstrb_r      <= 4'b0;
     pwrite_r     <= 1'b0;
     apb_is_write <= 1'b0;
   end else begin
     state <= next_state;

     if (state == IDLE) begin
       if (s_awvalid && s_awready) begin
         have_aw    <= 1'b1;
         awaddr_buf <= s_awaddr;
       end
       if (s_wvalid && s_wready) begin
         have_w    <= 1'b1;
         wdata_buf <= s_wdata;
         wstrb_buf <= s_wstrb;
       end
       if (s_arvalid && s_arready) begin
         have_ar    <= 1'b1;
         araddr_buf <= s_araddr;
       end
     end

     if ((state == IDLE) && (next_state == APB_SETUP)) begin
       if (have_ar) begin
         apb_is_write <= 1'b0;
         paddr_r      <= araddr_buf;
         pwdata_r     <= 32'b0;
         pstrb_r      <= 4'b0;
         pwrite_r     <= 1'b0;
         have_ar      <= 1'b0;
       end else begin
         apb_is_write <= 1'b1;
         paddr_r      <= awaddr_buf;
         pwdata_r     <= wdata_buf;
         pstrb_r      <= wstrb_buf;
         pwrite_r     <= 1'b1;
         have_aw      <= 1'b0;
         have_w       <= 1'b0;
       end
     end

     if (state == APB_ACCESS && pready) begin
       if (apb_is_write) begin
         bresp_r <= pslverr ? 2'b10 : 2'b00;
       end else begin
         rdata_r <= prdata;
         rresp_r <= pslverr ? 2'b10 : 2'b00;
       end
     end
   end
 end

endmodule
