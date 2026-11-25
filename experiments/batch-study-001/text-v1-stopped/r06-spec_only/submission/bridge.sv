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
  localparam [1:0] ST_IDLE   = 2'd0;
  localparam [1:0] ST_SETUP  = 2'd1;
  localparam [1:0] ST_ACCESS = 2'd2;
  localparam [1:0] ST_RESP   = 2'd3;

  logic [1:0] state;

  logic aw_have, w_have;
  logic [31:0] aw_addr_buf;
  logic [31:0] w_data_buf;
  logic [3:0]  w_strb_buf;

  logic active_write;
  logic [31:0] acc_addr;
  logic [31:0] acc_wdata;
  logic [3:0]  acc_wstrb;

  logic bvalid_r, rvalid_r;
  logic [1:0] bresp_r, rresp_r;
  logic [31:0] rdata_r;

  // A request can be accepted only when idle and no pending response
  wire idle_can_accept = (state == ST_IDLE) && !bvalid_r && !rvalid_r;

  assign s_awready = idle_can_accept && !aw_have;
  assign s_wready  = idle_can_accept && !w_have;

  // reads: only when nothing buffered, so no overlap of halves with read
  assign s_arready = idle_can_accept && !aw_have && !w_have;

  assign s_bvalid = bvalid_r;
  assign s_bresp  = bresp_r;
  assign s_rvalid = rvalid_r;
  assign s_rresp  = rresp_r;
  assign s_rdata  = rdata_r;

  assign psel    = (state == ST_SETUP) || (state == ST_ACCESS);
  assign penable = (state == ST_ACCESS);
  assign pwrite  = active_write;
  assign paddr   = acc_addr;
  assign pwdata  = active_write ? acc_wdata : 32'h0;
  assign pstrb   = active_write ? acc_wstrb : 4'h0;
  assign pprot   = 3'b000;

  always_ff @(posedge clk) begin
    if (!rst_n) begin
      state       <= ST_IDLE;
      aw_have     <= 1'b0;
      w_have      <= 1'b0;
      aw_addr_buf <= 32'h0;
      w_data_buf  <= 32'h0;
      w_strb_buf  <= 4'h0;
      active_write<= 1'b0;
      acc_addr    <= 32'h0;
      acc_wdata   <= 32'h0;
      acc_wstrb   <= 4'h0;
      bvalid_r    <= 1'b0;
      rvalid_r    <= 1'b0;
      bresp_r     <= 2'b00;
      rresp_r     <= 2'b00;
      rdata_r     <= 32'h0;
    end else begin
      // clear responses when accepted
      if (bvalid_r && s_bready) bvalid_r <= 1'b0;
      if (rvalid_r && s_rready) rvalid_r <= 1'b0;

      case (state)
        ST_IDLE: begin
          // capture AW
          if (s_awready && s_awvalid) begin
            aw_have     <= 1'b1;
            aw_addr_buf <= s_awaddr;
          end
          // capture W
          if (s_wready && s_wvalid) begin
            w_have     <= 1'b1;
            w_data_buf <= s_wdata;
            w_strb_buf <= s_wstrb;
          end
          // determine if both halves will be present after this cycle
          begin
            logic aw_after, w_after;
            logic [31:0] aw_addr_after, w_data_after;
            logic [3:0] w_strb_after;
            aw_after      = aw_have | (s_awready && s_awvalid);
            w_after       = w_have  | (s_wready  && s_wvalid);
            aw_addr_after = (s_awready && s_awvalid) ? s_awaddr : aw_addr_buf;
            w_data_after  = (s_wready  && s_wvalid)  ? s_wdata  : w_data_buf;
            w_strb_after  = (s_wready  && s_wvalid)  ? s_wstrb  : w_strb_buf;

            if (aw_after && w_after) begin
              // launch write: consume both halves
              aw_have      <= 1'b0;
              w_have       <= 1'b0;
              active_write <= 1'b1;
              acc_addr     <= aw_addr_after;
              acc_wdata    <= w_data_after;
              acc_wstrb    <= w_strb_after;
              state        <= ST_SETUP;
            end else if (s_arready && s_arvalid) begin
              active_write <= 1'b0;
              acc_addr     <= s_araddr;
              acc_wdata    <= 32'h0;
              acc_wstrb    <= 4'h0;
              state        <= ST_SETUP;
            end
          end
        end
        ST_SETUP: begin
          state <= ST_ACCESS;
        end
        ST_ACCESS: begin
          if (pready) begin
            if (active_write) begin
              bvalid_r <= 1'b1;
              bresp_r  <= pslverr ? 2'b10 : 2'b00;
            end else begin
              rvalid_r <= 1'b1;
              rresp_r  <= pslverr ? 2'b10 : 2'b00;
              rdata_r  <= prdata;
            end
            state <= ST_RESP;
          end
        end
        ST_RESP: begin
          if (active_write) begin
            if (bvalid_r && s_bready) state <= ST_IDLE;
          end else begin
            if (rvalid_r && s_rready) state <= ST_IDLE;
          end
        end
        default: state <= ST_IDLE;
      endcase
    end
  end
endmodule
