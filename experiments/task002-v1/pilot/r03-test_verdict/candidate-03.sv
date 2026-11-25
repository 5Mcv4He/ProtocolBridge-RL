module bridge(
 input logic clk,rst_n,
 input logic [31:0] s_awaddr, input logic s_awvalid, output logic s_awready,
 input logic [31:0] s_wdata, input logic [3:0] s_wstrb, input logic s_wvalid, output logic s_wready,
 output logic [1:0] s_bresp, output logic s_bvalid, input logic s_bready,
 input logic [31:0] s_araddr, input logic s_arvalid, output logic s_arready,
 output logic [31:0] s_rdata, output logic [1:0] s_rresp, output logic s_rvalid, input logic s_rready,
 output logic [31:0] paddr,pwdata, output logic [3:0] pstrb, output logic [2:0] pprot,
 output logic [2:0] psel, output logic penable,pwrite, input logic [95:0] prdata, input logic [2:0] pready,pslverr
);

 localparam [2:0] S_IDLE   = 3'd0;
 localparam [2:0] S_SETUP  = 3'd1;
 localparam [2:0] S_ACCESS = 3'd2;
 localparam [2:0] S_RESP   = 3'd3;

 logic [2:0] state;

 // write half buffers
 logic        aw_have, w_have;
 logic [31:0] aw_addr_buf, w_data_buf;
 logic [3:0]  w_strb_buf;

 // pending read request
 logic        ar_have;
 logic [31:0] ar_addr_buf;

 // APB transaction info
 logic [2:0]  tgt;
 logic [31:0] addr_base;
 logic [31:0] apb_addr;
 logic        apb_write;
 logic [31:0] apb_wdata;
 logic [3:0]  apb_strb;

 // response
 logic [1:0]  resp_buf;
 logic [31:0] rdata_buf;

 // decode helpers
 logic [2:0] dec_sel;
 logic [31:0] dec_addr;

 function automatic logic [2:0] decode_sel(input logic [31:0] a);
   if (a >= 32'h00001000 && a <= 32'h00001fff) decode_sel = 3'b001;
   else if (a >= 32'h00008000 && a <= 32'h00009fff) decode_sel = 3'b010;
   else if (a >= 32'h40000000 && a <= 32'h40000fff) decode_sel = 3'b100;
   else decode_sel = 3'b000;
 endfunction

 function automatic logic [31:0] decode_offset(input logic [31:0] a);
   if (a >= 32'h00001000 && a <= 32'h00001fff) decode_offset = a - 32'h00001000;
   else if (a >= 32'h00008000 && a <= 32'h00009fff) decode_offset = a - 32'h00008000;
   else decode_offset = a - 32'h40000000;
 endfunction

 assign s_awready = (state == S_IDLE) && rst_n && !aw_have && !(ar_have && 0);
 assign s_wready  = (state == S_IDLE) && rst_n && !w_have && !(ar_have && 0);
 assign s_arready = (state == S_IDLE) && rst_n && !aw_have && !w_have && !ar_have;

 always_ff @(posedge clk) begin
   if (!rst_n) begin
     state      <= S_IDLE;
     aw_have    <= 1'b0;
     w_have     <= 1'b0;
     aw_addr_buf<= 32'd0;
     w_data_buf <= 32'd0;
     w_strb_buf <= 4'd0;
     ar_have    <= 1'b0;
     ar_addr_buf<= 32'd0;
     tgt        <= 3'd0;
     addr_base  <= 32'd0;
     apb_addr   <= 32'd0;
     apb_write  <= 1'b0;
     apb_wdata  <= 32'd0;
     apb_strb   <= 4'd0;
     resp_buf   <= 2'b00;
     rdata_buf  <= 32'd0;
     psel       <= 3'd0;
     penable    <= 1'b0;
     pwrite     <= 1'b0;
     paddr      <= 32'd0;
     pwdata     <= 32'd0;
     pstrb      <= 4'd0;
     pprot      <= 3'd0;
     s_bvalid   <= 1'b0;
     s_bresp    <= 2'b00;
     s_rvalid   <= 1'b0;
     s_rresp    <= 2'b00;
     s_rdata    <= 32'd0;
   end else begin
     // defaults: psel/penable held unless changed below
     case (state)
       S_IDLE: begin
         psel    <= 3'd0;
         penable <= 1'b0;

         // accept AW
         if (s_awvalid && s_awready) begin
           aw_have     <= 1'b1;
           aw_addr_buf <= s_awaddr;
         end
         // accept W
         if (s_wvalid && s_wready) begin
           w_have     <= 1'b1;
           w_data_buf <= s_wdata;
           w_strb_buf <= s_wstrb;
         end
         // accept AR
         if (s_arvalid && s_arready) begin
           ar_have     <= 1'b1;
           ar_addr_buf <= s_araddr;
         end

         // process read immediately (takes priority)
         if (s_arvalid && s_arready) begin
           ar_have <= 1'b0;
           if (decode_sel(s_araddr) != 3'b000) begin
             tgt       <= decode_sel(s_araddr);
             apb_addr  <= decode_offset(s_araddr);
             apb_write <= 1'b0;
             apb_wdata <= 32'd0;
             apb_strb  <= 4'd0;
             paddr     <= decode_offset(s_araddr);
             pwrite    <= 1'b0;
             pwdata    <= 32'd0;
             pstrb     <= 4'd0;
             pprot     <= 3'd0;
             psel      <= decode_sel(s_araddr);
             penable   <= 1'b0;
             state     <= S_SETUP;
           end else begin
             s_rvalid <= 1'b1;
             s_rresp  <= 2'b11;
             s_rdata  <= 32'd0;
             state    <= S_RESP;
           end
         end else if (aw_have && w_have) begin
           // both halves already buffered
           if (decode_sel(aw_addr_buf) != 3'b000) begin
             tgt       <= decode_sel(aw_addr_buf);
             apb_addr  <= decode_offset(aw_addr_buf);
             apb_write <= 1'b1;
             apb_wdata <= w_data_buf;
             apb_strb  <= w_strb_buf;
             paddr     <= decode_offset(aw_addr_buf);
             pwrite    <= 1'b1;
             pwdata    <= w_data_buf;
             pstrb     <= w_strb_buf;
             pprot     <= 3'd0;
             psel      <= decode_sel(aw_addr_buf);
             penable   <= 1'b0;
             aw_have   <= 1'b0;
             w_have    <= 1'b0;
             state     <= S_SETUP;
           end else begin
             aw_have  <= 1'b0;
             w_have   <= 1'b0;
             s_bvalid <= 1'b1;
             s_bresp  <= 2'b11;
             state    <= S_RESP;
           end
         end else if ((aw_have || w_have) && !(s_awvalid && s_awready) && !(s_wvalid && s_wready)) begin
           // check newly completing
           if ((aw_have || (s_awvalid && s_awready)) && (w_have || (s_wvalid && s_wready))) begin
             logic [31:0] final_addr;
             final_addr = aw_have ? aw_addr_buf : s_awaddr;
             if (decode_sel(final_addr) != 3'b000) begin
               tgt       <= decode_sel(final_addr);
               apb_addr  <= decode_offset(final_addr);
               apb_write <= 1'b1;
               apb_wdata <= w_have ? w_data_buf : s_wdata;
               apb_strb  <= w_have ? w_strb_buf : s_wstrb;
               paddr     <= decode_offset(final_addr);
               pwrite    <= 1'b1;
               pwdata    <= w_have ? w_data_buf : s_wdata;
               pstrb     <= w_have ? w_strb_buf : s_wstrb;
               pprot     <= 3'd0;
               psel      <= decode_sel(final_addr);
               penable   <= 1'b0;
               aw_have   <= 1'b0;
               w_have    <= 1'b0;
               state     <= S_SETUP;
             end else begin
               aw_have  <= 1'b0;
               w_have   <= 1'b0;
               s_bvalid <= 1'b1;
               s_bresp  <= 2'b11;
               state    <= S_RESP;
             end
           end
         end
       end

       S_SETUP: begin
         penable <= 1'b1;
         state   <= S_ACCESS;
       end

       S_ACCESS: begin
         penable <= 1'b1;
         if (pready[tgt]) begin
           psel    <= 3'd0;
           penable <= 1'b0;
           if (apb_write) begin
             s_bvalid <= 1'b1;
             s_bresp  <= pslverr[tgt] ? 2'b10 : 2'b00;
             state    <= S_RESP;
           end else begin
             s_rvalid <= 1'b1;
             s_rresp  <= pslverr[tgt] ? 2'b10 : 2'b00;
             s_rdata  <= prdata[32*tgt +: 32];
             state    <= S_RESP;
           end
         end
       end

       S_RESP: begin
         psel    <= 3'd0;
         penable <= 1'b0;
         if (s_bvalid && s_bready) begin
           s_bvalid <= 1'b0;
           state    <= S_IDLE;
         end else if (s_rvalid && s_rready) begin
           s_rvalid <= 1'b0;
           state    <= S_IDLE;
         end
       end

       default: state <= S_IDLE;
     endcase
   end
 end
endmodule
