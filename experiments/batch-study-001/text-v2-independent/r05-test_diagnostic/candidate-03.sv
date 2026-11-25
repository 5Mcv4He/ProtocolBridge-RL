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

 // Buffered request halves
 logic        aw_have, w_have;
 logic [31:0] aw_addr_buf, w_data_buf;
 logic [3:0]  w_strb_buf;

 // APB FSM: 0=idle, 1=setup, 2=access
 logic [1:0]  state;

 // Response pending
 logic        b_pend, r_pend;
 logic [1:0]  b_resp_buf, r_resp_buf;
 logic [31:0] r_data_buf;

 // APB payload registers
 logic [31:0] a_addr, a_wdata;
 logic [3:0]  a_strb;
 logic        a_write;

 wire idle = (state == 2'd0);
 wire setup = (state == 2'd1);
 wire access = (state == 2'd2);

 // Ready when idle (or reset)
 assign s_awready = idle && !aw_have;
 assign s_wready  = idle && !w_have;
 assign s_arready = idle && !aw_have && !w_have && !b_pend && !r_pend;

 assign psel    = psel_r;
 assign penable = penable_r;
 assign pwrite  = a_write;
 assign paddr   = a_addr;
 assign pwdata  = a_write ? a_wdata : 32'b0;
 assign pstrb   = a_write ? a_strb : 4'b0;
 assign pprot   = 3'b000;

 logic psel_r, penable_r;

 assign s_bvalid = b_pend;
 assign s_bresp  = b_resp_buf;
 assign s_rvalid = r_pend;
 assign s_rdata  = r_data_buf;
 assign s_rresp  = r_resp_buf;

 wire both_wr = aw_have && w_have;
 wire launch_wr = idle && both_wr;
 wire launch_rd = idle && s_arvalid && !aw_have && !w_have && !b_pend && !r_pend;

 always_ff @(posedge clk) begin
   if (!rst_n) begin
     aw_have    <= 1'b0;
     w_have     <= 1'b0;
     aw_addr_buf<= 32'b0;
     w_data_buf <= 32'b0;
     w_strb_buf <= 4'b0;
     state      <= 2'd0;
     b_pend     <= 1'b0;
     r_pend     <= 1'b0;
     b_resp_buf <= 2'b00;
     r_resp_buf <= 2'b00;
     r_data_buf <= 32'b0;
     a_addr     <= 32'b0;
     a_wdata    <= 32'b0;
     a_strb     <= 4'b0;
     a_write    <= 1'b0;
     psel_r     <= 1'b0;
     penable_r  <= 1'b0;
   end else begin
     // Response handshakes
     if (b_pend && s_bready) b_pend <= 1'b0;
     if (r_pend && s_rready) r_pend <= 1'b0;

     // Accept write halves only when idle
     if (s_awready && s_awvalid) begin
       aw_have     <= 1'b1;
       aw_addr_buf <= s_awaddr;
     end
     if (s_wready && s_wvalid) begin
       w_have     <= 1'b1;
       w_data_buf <= s_wdata;
       w_strb_buf <= s_wstrb;
     end

     case (state)
       2'd0: begin
         psel_r    <= 1'b0;
         penable_r <= 1'b0;
         if (launch_wr) begin
           a_addr  <= aw_addr_buf;
           a_wdata <= w_data_buf;
           a_strb  <= w_strb_buf;
           a_write <= 1'b1;
           aw_have <= 1'b0;
           w_have  <= 1'b0;
           state   <= 2'd1;
           psel_r  <= 1'b1;
           penable_r<= 1'b0;
         end else if (launch_rd) begin
           a_addr  <= s_araddr;
           a_wdata <= 32'b0;
           a_strb  <= 4'b0;
           a_write <= 1'b0;
           state   <= 2'd1;
           psel_r  <= 1'b1;
           penable_r<= 1'b0;
         end
       end
       2'd1: begin
         psel_r    <= 1'b1;
         penable_r <= 1'b1;
         state     <= 2'd2;
       end
       2'd2: begin
         if (pready) begin
           state     <= 2'd0;
           psel_r    <= 1'b0;
           penable_r <= 1'b0;
           if (a_write) begin
             b_pend     <= 1'b1;
             b_resp_buf <= pslverr ? 2'b10 : 2'b00;
           end else begin
             r_pend     <= 1'b1;
             r_data_buf <= prdata;
             r_resp_buf <= pslverr ? 2'b10 : 2'b00;
           end
         end
       end
       default: begin
         state     <= 2'd0;
         psel_r    <= 1'b0;
         penable_r <= 1'b0;
       end
     endcase
   end
 end

endmodule
