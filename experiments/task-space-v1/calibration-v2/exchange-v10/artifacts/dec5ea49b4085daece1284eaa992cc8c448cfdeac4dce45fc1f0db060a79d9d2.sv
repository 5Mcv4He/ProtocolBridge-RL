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

 localparam [2:0] ST_IDLE=3'd0, ST_SETUP=3'd1, ST_ACCESS=3'd2, ST_BRESP=3'd3, ST_RRESP=3'd4;

 logic [2:0] state;
 logic aw_have, w_have;
 logic [31:0] aw_addr, w_data;
 logic [3:0] w_strb;
 logic [2:0] sel_r;
 logic [1:0] ridx;
 logic pwrite_r;
 logic [1:0] resp_reg;
 logic [31:0] rdata_reg;

 function automatic [2:0] dec(input logic [31:0] a);
   if (a >= 32'h00021000 && a <= 32'h00021fff) dec = 3'b001;
   else if (a >= 32'h00001000 && a <= 32'h00002fff) dec = 3'b010;
   else if (a >= 32'h80010000 && a <= 32'h80012fff) dec = 3'b100;
   else dec = 3'b000;
 endfunction

 function automatic [31:0] off(input logic [31:0] a, input logic [2:0] t);
   if (t == 3'b001) off = a - 32'h00021000;
   else if (t == 3'b010) off = a - 32'h00001000;
   else off = a - 32'h80010000;
 endfunction

 function automatic logic [1:0] ridx_of(input logic [2:0] t);
   if (t == 3'b001) ridx_of = 2'd0;
   else if (t == 3'b010) ridx_of = 2'd1;
   else ridx_of = 2'd2;
 endfunction

 function automatic logic rdyp(input logic [2:0] t, input logic [2:0] r);
   if (t == 3'b001) rdyp = r[0];
   else if (t == 3'b010) rdyp = r[1];
   else rdyp = r[2];
 endfunction

 function automatic logic errp(input logic [2:0] t, input logic [2:0] e);
   if (t == 3'b001) errp = e[0];
   else if (t == 3'b010) errp = e[1];
   else errp = e[2];
 endfunction

 function automatic logic [31:0] rdata_of(input logic [2:0] t, input logic [95:0] d);
   if (t == 3'b001) rdata_of = d[31:0];
   else if (t == 3'b010) rdata_of = d[63:32];
   else rdata_of = d[95:64];
 endfunction

 assign s_awready = (state == ST_IDLE) && !aw_have;
 assign s_wready  = (state == ST_IDLE) && !w_have;
 assign s_arready = (state == ST_IDLE) && !aw_have && !w_have;
 assign pprot = 3'b000;

 always_ff @(posedge clk) begin
   if (!rst_n) begin
     state <= ST_IDLE;
     aw_have <= 1'b0;
     w_have <= 1'b0;
     aw_addr <= 32'b0;
     w_data <= 32'b0;
     w_strb <= 4'b0;
     sel_r <= 3'b0;
     ridx <= 2'b0;
     pwrite_r <= 1'b0;
     resp_reg <= 2'b0;
     rdata_reg <= 32'b0;
     s_bvalid <= 1'b0;
     s_rvalid <= 1'b0;
     s_bresp <= 2'b0;
     s_rresp <= 2'b0;
     s_rdata <= 32'b0;
     psel <= 3'b0;
     penable <= 1'b0;
     paddr <= 32'b0;
     pwdata <= 32'b0;
     pstrb <= 4'b0;
     pwrite <= 1'b0;
   end else begin
     // default APB outputs
     if (state != ST_SETUP && state != ST_ACCESS) begin
       psel <= 3'b0;
       penable <= 1'b0;
     end

     // request acceptance
     if ((state == ST_IDLE) && s_awvalid && s_awready) begin
       aw_have <= 1'b1;
       aw_addr <= s_awaddr;
     end
     if ((state == ST_IDLE) && s_wvalid && s_wready) begin
       w_have <= 1'b1;
       w_data <= s_wdata;
       w_strb <= s_wstrb;
     end

     case (state)
       ST_IDLE: begin
         if (aw_have && w_have) begin
           if (dec(aw_addr) != 3'b000) begin
             state <= ST_SETUP;
             psel <= dec(aw_addr);
             penable <= 1'b0;
             paddr <= off(aw_addr, dec(aw_addr));
             pwdata <= w_data;
             pstrb <= w_strb;
             pwrite <= 1'b1;
             pwrite_r <= 1'b1;
             sel_r <= dec(aw_addr);
             ridx <= ridx_of(dec(aw_addr));
             aw_have <= 1'b0;
             w_have <= 1'b0;
           end else begin
             aw_have <= 1'b0;
             w_have <= 1'b0;
             s_bvalid <= 1'b1;
             s_bresp <= 2'b11;
             state <= ST_BRESP;
           end
         end else if (s_arvalid) begin
           if (dec(s_araddr) != 3'b000) begin
             state <= ST_SETUP;
             psel <= dec(s_araddr);
             penable <= 1'b0;
             paddr <= off(s_araddr, dec(s_araddr));
             pwrite <= 1'b0;
             pstrb <= 4'b0;
             pwrite_r <= 1'b0;
             sel_r <= dec(s_araddr);
             ridx <= ridx_of(dec(s_araddr));
           end else begin
             s_rvalid <= 1'b1;
             s_rresp <= 2'b11;
             s_rdata <= 32'b0;
             state <= ST_RRESP;
           end
         end
       end
       ST_SETUP: begin
         penable <= 1'b1;
         state <= ST_ACCESS;
       end
       ST_ACCESS: begin
         if (rdyp(sel_r, pready)) begin
           psel <= 3'b0;
           penable <= 1'b0;
           resp_reg <= errp(sel_r, pslverr) ? 2'b10 : 2'b00;
           rdata_reg <= rdata_of(sel_r, prdata);
           if (pwrite_r) begin
             s_bvalid <= 1'b1;
             s_bresp <= errp(sel_r, pslverr) ? 2'b10 : 2'b00;
             state <= ST_BRESP;
           end else begin
             s_rvalid <= 1'b1;
             s_rresp <= errp(sel_r, pslverr) ? 2'b10 : 2'b00;
             s_rdata <= rdata_of(sel_r, prdata);
             state <= ST_RRESP;
           end
         end
       end
       ST_BRESP: begin
         if (s_bready) begin
           s_bvalid <= 1'b0;
           state <= ST_IDLE;
         end
       end
       ST_RRESP: begin
         if (s_rready) begin
           s_rvalid <= 1'b0;
           state <= ST_IDLE;
         end
       end
       default: state <= ST_IDLE;
     endcase
   end
 end

endmodule
