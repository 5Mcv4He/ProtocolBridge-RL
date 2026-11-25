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

 // State encoding
 localparam logic [1:0]
   IDLE     = 2'd0,
   APB_SETUP= 2'd1,
   APB_ACCESS=2'd2,
   RESP     = 2'd3;

 logic [1:0] state;

 // Buffered write halves
 logic aw_have;
 logic [31:0] aw_addr;
 logic w_have;
 logic [31:0] w_data;
 logic [3:0]  w_strb;

 // Buffered read request
 logic ar_have;
 logic [31:0] ar_addr;

 // Pending response info
 logic resp_is_write;
 logic [31:0] resp_rdata;
 logic [1:0]  resp_resp;

 // Latched APB control signals
 logic [31:0] apb_addr;
 logic        apb_write;
 logic [31:0] apb_wdata;
 logic [3:0]  apb_strb;

 wire aw_ready_now = rst_n && state==IDLE && !aw_have && !w_have && !ar_have && !s_rvalid && !s_bvalid;
 wire w_ready_now  = rst_n && state==IDLE && !aw_have && !w_have && !ar_have && !s_rvalid && !s_bvalid;
 wire ar_ready_now = rst_n && state==IDLE && !ar_have && !aw_have && !w_have && !s_rvalid && !s_bvalid;

 assign s_awready = aw_ready_now;
 assign s_wready  = w_ready_now;
 assign s_arready = ar_ready_now;

 assign pprot = 3'b000;

 always_ff @(posedge clk) begin
   if (!rst_n) begin
     state        <= IDLE;
     aw_have      <= 1'b0;
     aw_addr      <= 32'b0;
     w_have       <= 1'b0;
     w_data       <= 32'b0;
     w_strb       <= 4'b0;
     ar_have      <= 1'b0;
     ar_addr      <= 32'b0;
     resp_is_write<= 1'b0;
     resp_rdata   <= 32'b0;
     resp_resp    <= 2'b00;
     apb_addr     <= 32'b0;
     apb_write    <= 1'b0;
     apb_wdata    <= 32'b0;
     apb_strb     <= 4'b0;
     psel         <= 1'b0;
     penable      <= 1'b0;
     pwrite       <= 1'b0;
     paddr        <= 32'b0;
     pwdata       <= 32'b0;
     pstrb        <= 4'b0;
     s_bresp      <= 2'b00;
     s_bvalid     <= 1'b0;
     s_rdata      <= 32'b0;
     s_rresp      <= 2'b00;
     s_rvalid     <= 1'b0;
   end else begin
     // Default: keep outputs; clear psel/penable unless set below
     psel    <= 1'b0;
     penable <= 1'b0;

     case (state)
       IDLE: begin
         // Accept write halves
         if (s_awvalid && s_awready) begin
           aw_have <= 1'b1;
           aw_addr <= s_awaddr;
         end
         if (s_wvalid && s_wready) begin
           w_have <= 1'b1;
           w_data <= s_wdata;
           w_strb <= s_wstrb;
         end
         // Accept read request
         if (s_arvalid && s_arready) begin
           ar_have <= 1'b1;
           ar_addr <= s_araddr;
         end

         // Decide what to launch next (use combinational view including this cycle)
         if (ar_have || (s_arvalid && s_arready)) begin
           // read request pending
           apb_addr     <= ar_have ? ar_addr : s_araddr;
           apb_write    <= 1'b0;
           apb_wdata    <= 32'b0;
           apb_strb     <= 4'b0;
           resp_is_write<= 1'b0;
           ar_have      <= 1'b0;
           state        <= APB_SETUP;
           psel         <= 1'b1;
           penable      <= 1'b0;
           pwrite       <= 1'b0;
           paddr        <= ar_have ? ar_addr : s_araddr;
           pwdata       <= 32'b0;
           pstrb        <= 4'b0;
         end else if (aw_have || (s_awvalid && s_awready)) begin
           logic ah;
           logic [31:0] aaddr;
           logic wh;
           logic [31:0] wd;
           logic [3:0]  ws;
           ah    = aw_have || (s_awvalid && s_awready);
           aaddr = aw_have ? aw_addr : s_awaddr;
           wh    = w_have  || (s_wvalid && s_wready);
           wd    = w_have  ? w_data : s_wdata;
           ws    = w_have  ? w_strb : s_wstrb;
           if (ah && wh) begin
             apb_addr     <= aaddr;
             apb_write    <= 1'b1;
             apb_wdata    <= wd;
             apb_strb     <= ws;
             resp_is_write<= 1'b1;
             aw_have      <= 1'b0;
             w_have       <= 1'b0;
             state        <= APB_SETUP;
             psel         <= 1'b1;
             penable      <= 1'b0;
             pwrite       <= 1'b1;
             paddr        <= aaddr;
             pwdata       <= wd;
             pstrb        <= ws;
           end
         end
       end

       APB_SETUP: begin
         psel    <= 1'b1;
         penable <= 1'b1;
         paddr   <= apb_addr;
         pwrite  <= apb_write;
         pwdata  <= apb_write ? apb_wdata : 32'b0;
         pstrb   <= apb_write ? apb_strb  : 4'b0;
         // note: pready is sampled in APB_ACCESS next cycle
         state   <= APB_ACCESS;
       end

       APB_ACCESS: begin
         psel    <= 1'b1;
         penable <= 1'b1;
         paddr   <= apb_addr;
         pwrite  <= apb_write;
         pwdata  <= apb_write ? apb_wdata : 32'b0;
         pstrb   <= apb_write ? apb_strb  : 4'b0;
         if (pready) begin
           resp_resp    <= pslverr ? 2'b10 : 2'b00;
           resp_rdata   <= prdata;
           state        <= RESP;
           if (apb_write) begin
             s_bvalid <= 1'b1;
             s_bresp  <= pslverr ? 2'b10 : 2'b00;
           end else begin
             s_rvalid <= 1'b1;
             s_rdata  <= prdata;
             s_rresp  <= pslverr ? 2'b10 : 2'b00;
           end
         end
       end

       RESP: begin
         // Keep response valid/payload stable until handshake
         if (apb_write) begin
           s_bvalid <= 1'b1;
           s_bresp  <= resp_resp;
           if (s_bready) begin
             s_bvalid <= 1'b0;
             state    <= IDLE;
           end
         end else begin
           s_rvalid <= 1'b1;
           s_rdata  <= resp_rdata;
           s_rresp  <= resp_resp;
           if (s_rready) begin
             s_rvalid <= 1'b0;
             state    <= IDLE;
           end
         end
       end

       default: state <= IDLE;
     endcase
   end
 end

endmodule
