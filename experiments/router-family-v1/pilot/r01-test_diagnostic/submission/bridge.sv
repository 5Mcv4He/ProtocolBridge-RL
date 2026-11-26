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

 // state machine
 localparam IDLE   = 3'd0;
 localparam WSETUP = 3'd1;
 localparam WACC   = 3'd2;
 localparam WRESP  = 3'd3;
 localparam RSETUP = 3'd4;
 localparam RACC   = 3'd5;
 localparam RRESP  = 3'd6;

 logic [2:0] state;

 // write half buffers
 logic        aw_have, w_have;
 logic [31:0] aw_addr;
 logic [31:0] w_data;
 logic [3:0]  w_strb;

 // APB request info captured
 logic [2:0]  tgt;
 logic [31:0] local_addr;
 logic [31:0] xfer_wdata;
 logic [3:0]  xfer_wstrb;
 logic        xfer_write;
 logic        xfer_mapped;

 // response buffers
 logic [1:0]  bresp_r, rresp_r;
 logic [31:0] rdata_r;

 function automatic logic [2:0] decode(input logic [31:0] a);
   begin
     if (a >= 32'h00021000 && a <= 32'h00023fff) decode = 3'b001;
     else if (a >= 32'h00001000 && a <= 32'h00002fff) decode = 3'b010;
     else if (a >= 32'h80001000 && a <= 32'h80001fff) decode = 3'b100;
     else decode = 3'b000;
   end
 endfunction

 function automatic logic [31:0] offset_of(input logic [2:0] t, input logic [31:0] a);
   begin
     case (t)
       3'b001: offset_of = a - 32'h00021000;
       3'b010: offset_of = a - 32'h00001000;
       3'b100: offset_of = a - 32'h80001000;
       default: offset_of = a;
     endcase
   end
 endfunction

 // completion pulse from selected APB target
 wire [2:0] ready_masked = pready & psel;
 wire comp = (ready_masked != 3'b000);
 wire comp_err = (pslverr & ready_masked) != 3'b000;

 // selected target read data
 logic [31:0] sel_rdata;
 always_comb begin
   case (psel)
     3'b001: sel_rdata = prdata[31:0];
     3'b010: sel_rdata = prdata[63:32];
     3'b100: sel_rdata = prdata[95:64];
     default: sel_rdata = 32'd0;
   endcase
 end

 // outputs
 assign s_awready = (rst_n && state == IDLE && !aw_have);
 assign s_wready  = (rst_n && state == IDLE && !w_have);
 assign s_arready = (rst_n && state == IDLE && !aw_have && !w_have);

 assign s_bvalid = (rst_n && state == WRESP);
 assign s_bresp  = bresp_r;
 assign s_rvalid = (rst_n && state == RRESP);
 assign s_rresp  = rresp_r;
 assign s_rdata  = rdata_r;

 assign psel    = (state == WSETUP || state == WACC || state == RSETUP || state == RACC) ? tgt : 3'b000;
 assign penable = (state == WACC || state == RACC);
 assign pwrite  = xfer_write;
 assign paddr   = local_addr;
 assign pwdata  = xfer_wdata;
 assign pstrb   = xfer_wstrb;
 assign pprot   = 3'b000;

 always_ff @(posedge clk) begin
   if (!rst_n) begin
     state    <= IDLE;
     aw_have  <= 1'b0;
     w_have   <= 1'b0;
     aw_addr  <= 32'd0;
     w_data   <= 32'd0;
     w_strb   <= 4'd0;
     tgt      <= 3'b000;
     local_addr <= 32'd0;
     xfer_wdata <= 32'd0;
     xfer_wstrb <= 4'd0;
     xfer_write <= 1'b0;
     xfer_mapped <= 1'b0;
     bresp_r  <= 2'b00;
     rresp_r  <= 2'b00;
     rdata_r  <= 32'd0;
   end else begin
     case (state)
       IDLE: begin
         if (s_awvalid && s_awready) begin
           aw_have <= 1'b1;
           aw_addr <= s_awaddr;
         end
         if (s_wvalid && s_wready) begin
           w_have  <= 1'b1;
           w_data  <= s_wdata;
           w_strb  <= s_wstrb;
         end

         if (s_arvalid && s_arready) begin
           // start read
           tgt        <= decode(s_araddr);
           local_addr <= offset_of(decode(s_araddr), s_araddr);
           xfer_write <= 1'b0;
           xfer_wdata <= 32'd0;
           xfer_wstrb <= 4'd0;
           if (decode(s_araddr) == 3'b000) begin
             xfer_mapped <= 1'b0;
             rdata_r <= 32'd0;
             rresp_r <= 2'b11;
             state   <= RRESP;
           end else begin
             xfer_mapped <= 1'b1;
             state   <= RSETUP;
           end
         end else begin
           // handle write completion check
           if ((aw_have || (s_awvalid && s_awready)) &&
               (w_have  || (s_wvalid  && s_wready))) begin
             begin
               logic [31:0] a;
               logic [2:0]  t;
               a = aw_have ? aw_addr : s_awaddr;
               t = decode(a);
               tgt        <= t;
               local_addr <= offset_of(t, a);
               xfer_write <= 1'b1;
               xfer_wdata <= w_have ? w_data : s_wdata;
               xfer_wstrb <= w_have ? w_strb : s_wstrb;
               if (t == 3'b000) begin
                 xfer_mapped <= 1'b0;
                 bresp_r <= 2'b11;
                 state   <= WRESP;
                 aw_have <= 1'b0;
                 w_have  <= 1'b0;
               end else begin
                 xfer_mapped <= 1'b1;
                 state   <= WSETUP;
                 aw_have <= 1'b0;
                 w_have  <= 1'b0;
               end
             end
           end
         end
       end

       WSETUP: begin
         state <= WACC;
       end

       WACC: begin
         if (comp) begin
           bresp_r <= comp_err ? 2'b10 : 2'b00;
           state   <= WRESP;
         end
       end

       WRESP: begin
         if (s_bready) begin
           state <= IDLE;
         end
       end

       RSETUP: begin
         state <= RACC;
       end

       RACC: begin
         if (comp) begin
           rdata_r <= sel_rdata;
           rresp_r <= comp_err ? 2'b10 : 2'b00;
           state   <= RRESP;
         end
       end

       RRESP: begin
         if (s_rready) begin
           state <= IDLE;
         end
       end

       default: state <= IDLE;
     endcase
   end
 end

endmodule
