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
 localparam [1:0] ST_IDLE=2'd0, ST_SETUP=2'd1, ST_ACCESS=2'd2, ST_RESP=2'd3;

 logic [1:0] state;
 logic aw_held, w_held;
 logic [31:0] aw_addr, w_data;
 logic [3:0] w_strb;
 logic sel;          // 0 = write, 1 = read
 logic mapped;
 logic [1:0] tgt;
 logic [31:0] lat_addr;
 logic [31:0] lat_wdata;
 logic [3:0] lat_strb;
 logic [1:0] resp_code;
 logic [31:0] resp_data;

 function automatic logic [1:0] decode(input logic [31:0] a);
   if (a >= 32'h0010000c && a <= 32'h00102017) decode = 2'd0;
   else if (a >= 32'hfffffff4 && a <= 32'hfffffff7) decode = 2'd1;
   else if (a >= 32'h7000000c && a <= 32'h7000008b) decode = 2'd2;
   else decode = 2'd3;
 endfunction

 function automatic logic [31:0] local_addr(input logic [31:0] a, input logic [1:0] s);
   case (s)
     2'd0: local_addr = a - 32'h0010000c;
     2'd1: local_addr = a - 32'hfffffff4;
     2'd2: local_addr = a - 32'h7000000c;
     default: local_addr = 32'h0;
   endcase
 endfunction

 wire [1:0] dec_aw = decode(s_awaddr);
 wire [1:0] dec_ar = decode(s_araddr);
 wire take_aw = (state==ST_IDLE) && !aw_held && s_awvalid;
 wire take_w  = (state==ST_IDLE) && !w_held && s_wvalid;
 wire have_aw = aw_held || take_aw;
 wire have_w  = w_held  || take_w;
 wire [1:0] tgt_now = aw_held ? decode(aw_addr) : dec_aw;
 wire [31:0] addr_now = aw_held ? aw_addr : s_awaddr;

 assign s_awready = (state==ST_IDLE) && !aw_held;
 assign s_wready  = (state==ST_IDLE) && !w_held;
 assign s_arready = (state==ST_IDLE) && !aw_held && !w_held;

 assign s_bvalid = (state==ST_RESP) && !sel;
 assign s_bresp  = resp_code;
 assign s_rvalid = (state==ST_RESP) && sel;
 assign s_rdata  = resp_data;
 assign s_rresp  = resp_code;

 assign psel = (mapped && (state==ST_SETUP || state==ST_ACCESS)) ? (3'd1 << tgt) : 3'd0;
 assign penable = mapped && (state==ST_ACCESS);
 assign pwrite = !sel;
 assign paddr = mapped ? local_addr(lat_addr, tgt) : 32'h0;
 assign pwdata = lat_wdata;
 assign pstrb = (!sel) ? lat_strb : 4'd0;
 assign pprot = 3'b000;

 wire apb_done = mapped && (state==ST_ACCESS) && pready[tgt];

 always_ff @(posedge clk) begin
   if (!rst_n) begin
     state <= ST_IDLE;
     aw_held <= 1'b0;
     w_held <= 1'b0;
     aw_addr <= 32'h0;
     w_data <= 32'h0;
     w_strb <= 4'h0;
     sel <= 1'b0;
     mapped <= 1'b0;
     tgt <= 2'd0;
     lat_addr <= 32'h0;
     lat_wdata <= 32'h0;
     lat_strb <= 4'h0;
     resp_code <= 2'b00;
     resp_data <= 32'h0;
   end else begin
     case (state)
       ST_IDLE: begin
         if (s_arvalid && s_arready) begin
           lat_addr <= s_araddr;
           lat_wdata <= 32'h0;
           lat_strb <= 4'h0;
           sel <= 1'b1;
           tgt <= dec_ar;
           mapped <= (dec_ar != 2'd3);
           if (dec_ar == 2'd3) begin
             resp_code <= 2'b11;
             resp_data <= 32'h0;
             state <= ST_RESP;
           end else begin
             state <= ST_SETUP;
           end
         end else begin
           if (take_aw) begin
             aw_held <= 1'b1;
             aw_addr <= s_awaddr;
           end
           if (take_w) begin
             w_held <= 1'b1;
             w_data <= s_wdata;
             w_strb <= s_wstrb;
           end
           if (have_aw && have_w) begin
             lat_addr  <= addr_now;
             lat_wdata <= take_w ? s_wdata : w_data;
             lat_strb  <= take_w ? s_wstrb : w_strb;
             sel <= 1'b0;
             tgt <= tgt_now;
             mapped <= (tgt_now != 2'd3);
             aw_held <= 1'b0;
             w_held <= 1'b0;
             if (tgt_now == 2'd3) begin
               resp_code <= 2'b11;
               state <= ST_RESP;
             end else begin
               state <= ST_SETUP;
             end
           end
         end
       end

       ST_SETUP: begin
         state <= ST_ACCESS;
       end

       ST_ACCESS: begin
         if (apb_done) begin
           resp_code <= pslverr[tgt] ? 2'b10 : 2'b00;
           resp_data <= sel ? prdata[32*tgt +: 32] : 32'h0;
           state <= ST_RESP;
         end
       end

       ST_RESP: begin
         if (sel ? s_rready : s_bready) state <= ST_IDLE;
       end

       default: state <= ST_IDLE;
     endcase
   end
 end
endmodule
