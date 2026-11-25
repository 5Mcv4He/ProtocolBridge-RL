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

 // APB transaction info
 logic [2:0]  tgt;
 logic        apb_write;

 function automatic logic [2:0] dec(input logic [31:0] a);
   if (a >= 32'h00001000 && a <= 32'h00001fff) dec = 3'b001;
   else if (a >= 32'h00008000 && a <= 32'h00009fff) dec = 3'b010;
   else if (a >= 32'h40000000 && a <= 32'h40000fff) dec = 3'b100;
   else dec = 3'b000;
 endfunction

 function automatic logic [31:0] off(input logic [31:0] a);
   if (a >= 32'h00001000 && a <= 32'h00001fff) off = a - 32'h00001000;
   else if (a >= 32'h00008000 && a <= 32'h00009fff) off = a - 32'h00008000;
   else off = a - 32'h40000000;
 endfunction

 assign s_awready = (state == S_IDLE) && !aw_have && rst_n;
 assign s_wready  = (state == S_IDLE) && !w_have && rst_n;
 assign s_arready = (state == S_IDLE) && !aw_have && !w_have && rst_n;

 // combinational values for start decisions
 logic        aw_now, w_now, aw_full;
 logic [31:0] fa, fd;
 logic [3:0]  fs;

 assign aw_now = aw_have | (s_awvalid & s_awready);
 assign w_now  = w_have  | (s_wvalid  & s_wready);
 assign aw_full= aw_now & w_now;
 assign fa = aw_have ? aw_addr_buf : s_awaddr;
 assign fd = w_have  ? w_data_buf  : s_wdata;
 assign fs = w_have  ? w_strb_buf  : s_wstrb;

 always_ff @(posedge clk) begin
   if (!rst_n) begin
     state       <= S_IDLE;
     aw_have     <= 1'b0;
     w_have      <= 1'b0;
     aw_addr_buf <= 32'd0;
     w_data_buf  <= 32'd0;
     w_strb_buf  <= 4'd0;
     tgt         <= 3'd0;
     apb_write   <= 1'b0;
     psel        <= 3'd0;
     penable     <= 1'b0;
     pwrite      <= 1'b0;
     paddr       <= 32'd0;
     pwdata      <= 32'd0;
     pstrb       <= 4'd0;
     pprot       <= 3'd0;
     s_bvalid    <= 1'b0;
     s_bresp     <= 2'b00;
     s_rvalid    <= 1'b0;
     s_rresp     <= 2'b00;
     s_rdata     <= 32'd0;
   end else begin
     case (state)
       S_IDLE: begin
         psel    <= 3'd0;
         penable <= 1'b0;

         if (s_arvalid && s_arready) begin
           if (dec(s_araddr) != 3'b000) begin
             tgt       <= dec(s_araddr);
             apb_write <= 1'b0;
             paddr     <= off(s_araddr);
             pwrite    <= 1'b0;
             pwdata    <= 32'd0;
             pstrb     <= 4'd0;
             pprot     <= 3'd0;
             psel      <= dec(s_araddr);
             penable   <= 1'b0;
             state     <= S_SETUP;
             aw_have   <= aw_now;
             w_have    <= w_now;
             if (aw_now) aw_addr_buf <= s_awaddr;
             if (w_now) begin
               w_data_buf <= s_wdata;
               w_strb_buf <= s_wstrb;
             end
           end else begin
             s_rvalid <= 1'b1;
             s_rresp  <= 2'b11;
             s_rdata  <= 32'd0;
             state    <= S_RESP;
           end
         end else if (aw_full) begin
           if (dec(fa) != 3'b000) begin
             tgt       <= dec(fa);
             apb_write <= 1'b1;
             paddr     <= off(fa);
             pwrite    <= 1'b1;
             pwdata    <= fd;
             pstrb     <= fs;
             pprot     <= 3'd0;
             psel      <= dec(fa);
             penable   <= 1'b0;
             state     <= S_SETUP;
           end else begin
             s_bvalid <= 1'b1;
             s_bresp  <= 2'b11;
             state    <= S_RESP;
           end
           aw_have <= 1'b0;
           w_have  <= 1'b0;
         end else begin
           if (aw_now) begin
             aw_have     <= 1'b1;
             aw_addr_buf <= s_awaddr;
           end
           if (w_now) begin
             w_have     <= 1'b1;
             w_data_buf <= s_wdata;
             w_strb_buf <= s_wstrb;
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
           end else begin
             s_rvalid <= 1'b1;
             s_rresp  <= pslverr[tgt] ? 2'b10 : 2'b00;
             s_rdata  <= prdata[32*tgt +: 32];
           end
           state <= S_RESP;
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
