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
 localparam IDLE=3'd0, SETUP=3'd1, ACCESS=3'd2, RESP=3'd3;

 logic [2:0] state;
 logic is_write;

 logic aw_buf_v;
 logic [31:0] aw_buf_a;
 logic w_buf_v;
 logic [31:0] w_buf_d;
 logic [3:0] w_buf_s;

 logic [31:0] paddr_r, pwdata_r;
 logic [3:0] pstrb_r;
 logic pwrite_r;
 logic [31:0] rdata_r;
 logic [1:0] resp_r;

 wire idle = (state == IDLE);

 // Write halves may be accepted independently; once both present we launch.
 assign s_awready = rst_n && idle && !aw_buf_v;
 assign s_wready  = rst_n && idle && !w_buf_v;
 // Read accepted only when no write half is buffered (avoid mixing).
 assign s_arready = rst_n && idle && !aw_buf_v && !w_buf_v;

 assign s_bvalid = rst_n && (state == RESP) && is_write;
 assign s_bresp  = resp_r;
 assign s_rvalid = rst_n && (state == RESP) && !is_write;
 assign s_rdata  = rdata_r;
 assign s_rresp  = resp_r;

 assign paddr   = paddr_r;
 assign psel    = rst_n && (state == SETUP || state == ACCESS);
 assign penable = rst_n && (state == ACCESS);
 assign pwrite  = pwrite_r;
 assign pwdata  = pwdata_r;
 assign pstrb   = pstrb_r;
 assign pprot   = 3'b000;

 wire aw_hs = s_awvalid && s_awready;
 wire w_hs  = s_wvalid  && s_wready;
 wire ar_hs = s_arvalid && s_arready;
 wire b_hs  = s_bvalid  && s_bready;
 wire r_hs  = s_rvalid  && s_rready;

 always @(posedge clk) begin
  if (!rst_n) begin
   state <= IDLE;
   is_write <= 1'b0;
   aw_buf_v <= 1'b0;
   aw_buf_a <= 32'b0;
   w_buf_v  <= 1'b0;
   w_buf_d  <= 32'b0;
   w_buf_s  <= 4'b0;
   paddr_r  <= 32'b0;
   pwdata_r <= 32'b0;
   pstrb_r  <= 4'b0;
   pwrite_r <= 1'b0;
   rdata_r  <= 32'b0;
   resp_r   <= 2'b00;
  end else begin
   case (state)
    IDLE: begin
     if (aw_hs) begin aw_buf_v <= 1'b1; aw_buf_a <= s_awaddr; end
     if (w_hs)  begin w_buf_v <= 1'b1; w_buf_d <= s_wdata; w_buf_s <= s_wstrb; end
     if ((aw_buf_v || aw_hs) && (w_buf_v || w_hs)) begin
      is_write <= 1'b1;
      paddr_r  <= aw_hs ? s_awaddr : aw_buf_a;
      pwdata_r <= w_hs  ? s_wdata  : w_buf_d;
      pstrb_r  <= w_hs  ? s_wstrb  : w_buf_s;
      pwrite_r <= 1'b1;
      aw_buf_v <= 1'b0;
      w_buf_v  <= 1'b0;
      state    <= SETUP;
     end else if (ar_hs) begin
      is_write <= 1'b0;
      paddr_r  <= s_araddr;
      pwdata_r <= 32'b0;
      pstrb_r  <= 4'b0;
      pwrite_r <= 1'b0;
      state    <= SETUP;
     end
    end
    SETUP: state <= ACCESS;
    ACCESS: if (pready) begin
     state   <= RESP;
     rdata_r <= prdata;
     resp_r  <= pslverr ? 2'b10 : 2'b00;
    end
    RESP: if (is_write ? b_hs : r_hs) state <= IDLE;
    default: state <= IDLE;
   endcase
  end
 end
endmodule
