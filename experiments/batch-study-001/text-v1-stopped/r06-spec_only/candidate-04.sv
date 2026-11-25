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
  logic [31:0] aw_addr_r;
  logic [31:0] w_data_r;
  logic [3:0]  w_strb_r;

  logic is_write;
  logic [31:0] addr_r;
  logic [31:0] wdata_hold;
  logic [3:0]  wstrb_hold;

  logic bvalid_r, rvalid_r;
  logic [1:0] bresp_r, rresp_r;
  logic [31:0] rdata_r;

  logic wr_launched;

  assign s_awready = (state == ST_IDLE) && !aw_have && !bvalid_r && !is_write_pending();
  assign s_wready  = (state == ST_IDLE) && !w_have && !bvalid_r && !is_write_pending();

  // helper: is there an active write transaction not yet complete
  function automatic logic is_write_pending();
    return (state != ST_IDLE) && is_write;
  endfunction

  assign s_arready = (state == ST_IDLE) && !rvalid_r && !aw_have && !w_have &&
                     !is_write_pending();

  assign s_bvalid = bvalid_r;
  assign s_bresp  = bresp_r;
  assign s_rvalid = rvalid_r;
  assign s_rresp  = rresp_r;
  assign s_rdata  = rdata_r;

  assign psel    = (state == ST_SETUP) || (state == ST_ACCESS);
  assign penable = (state == ST_ACCESS);
  assign pwrite  = is_write;
  assign paddr   = addr_r;
  assign pwdata  = is_write ? wdata_hold : 32'h0;
  assign pstrb   = is_write ? wstrb_hold : 4'h0;
  assign pprot   = 3'b000;

  logic do_apb_complete;
  assign do_apb_complete = (state == ST_ACCESS) && pready;

  always_ff @(posedge clk) begin
    if (!rst_n) begin
      state      <= ST_IDLE;
      aw_have    <= 1'b0;
      w_have     <= 1'b0;
      aw_addr_r  <= 32'h0;
      w_data_r   <= 32'h0;
      w_strb_r   <= 4'h0;
      is_write   <= 1'b0;
      addr_r     <= 32'h0;
      wdata_hold <= 32'h0;
      wstrb_hold <= 4'h0;
      bvalid_r   <= 1'b0;
      rvalid_r   <= 1'b0;
      bresp_r    <= 2'b00;
      rresp_r    <= 2'b00;
      rdata_r    <= 32'h0;
    end else begin
      // defaults: responses drop when accepted
      if (bvalid_r && s_bready) bvalid_r <= 1'b0;
      if (rvalid_r && s_rready) rvalid_r <= 1'b0;

      case (state)
        ST_IDLE: begin
          // accept write halves
          if (s_awready && s_awvalid) begin
            aw_have   <= 1'b1;
            aw_addr_r <= s_awaddr;
          end
          if (s_wready && s_wvalid) begin
            w_have   <= 1'b1;
            w_data_r <= s_wdata;
            w_strb_r <= s_wstrb;
          end
          // acceptance of the second half launches write
          if (aw_have && w_have) begin
            // shouldn't happen in IDLE normally (we leave IDLE when both present)
          end else if (aw_have && s_wready && s_wvalid) begin
            // complete write
            aw_have    <= 1'b0;
            w_have     <= 1'b0;
            is_write   <= 1'b1;
            addr_r     <= aw_addr_r;
            wdata_hold <= s_wdata;
            wstrb_hold <= s_wstrb;
            state      <= ST_SETUP;
          end else if (w_have && s_awready && s_awvalid) begin
            aw_have    <= 1'b0;
            w_have     <= 1'b0;
            is_write   <= 1'b1;
            addr_r     <= s_awaddr;
            wdata_hold <= w_data_r;
            wstrb_hold <= w_strb_r;
            state      <= ST_SETUP;
          end else if (aw_have && w_have) begin
            // both buffered from prior? not expected here, but handle
            aw_have    <= 1'b0;
            w_have     <= 1'b0;
            is_write   <= 1'b1;
            addr_r     <= aw_addr_r;
            wdata_hold <= w_data_r;
            wstrb_hold <= w_strb_r;
            state      <= ST_SETUP;
          end else if (s_arready && s_arvalid) begin
            is_write <= 1'b0;
            addr_r   <= s_araddr;
            state    <= ST_SETUP;
          end
        end
        ST_SETUP: begin
          state <= ST_ACCESS;
        end
        ST_ACCESS: begin
          if (pready) begin
            if (is_write) begin
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
          if (is_write) begin
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
