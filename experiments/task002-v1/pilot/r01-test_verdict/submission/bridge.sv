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

  function automatic logic [2:0] decode(input logic [31:0] a);
    if (a >= 32'h0000_1000 && a <= 32'h0000_1ffc) decode = 3'b001;
    else if (a >= 32'h0000_8000 && a <= 32'h0000_9ffc) decode = 3'b010;
    else if (a >= 32'h4000_0000 && a <= 32'h4000_0ffc) decode = 3'b100;
    else decode = 3'b000;
  endfunction

  function automatic logic [31:0] local_off(input logic [31:0] a);
    if (a >= 32'h0000_1000 && a <= 32'h0000_1fff) local_off = a - 32'h0000_1000;
    else if (a >= 32'h0000_8000 && a <= 32'h0000_9fff) local_off = a - 32'h0000_8000;
    else local_off = a - 32'h4000_0000;
  endfunction

  typedef enum logic [2:0] {
    IDLE,
    SETUP,
    ACCESS,
    RESP
  } state_t;

  state_t state;

  logic        aw_have, w_have;
  logic [31:0] aw_addr;
  logic [31:0] w_data;
  logic [3:0]  w_strb;

  logic [2:0]  sel_q;
  logic [31:0] paddr_q, pwdata_q;
  logic [3:0]  pstrb_q;
  logic        pwrite_q;

  logic        bvalid_q, rvalid_q;
  logic [1:0]  bresp_q, rresp_q;
  logic [31:0] rdata_q;

  assign s_awready = (state == IDLE) && !aw_have;
  assign s_wready  = (state == IDLE) && !w_have;
  assign s_arready = (state == IDLE) && !aw_have && !w_have && !s_awvalid && !s_wvalid && !bvalid_q && !rvalid_q;

  assign psel    = sel_q;
  assign penable = (state == ACCESS);
  assign paddr   = paddr_q;
  assign pwrite  = pwrite_q;
  assign pwdata  = pwdata_q;
  assign pstrb   = pstrb_q;
  assign pprot   = 3'b000;

  assign s_bvalid = bvalid_q;
  assign s_bresp  = bresp_q;
  assign s_rvalid = rvalid_q;
  assign s_rdata  = rdata_q;
  assign s_rresp  = rresp_q;

  logic start_write_ns;
  logic [31:0] start_waddr;
  logic [31:0] start_wdata;
  logic [3:0]  start_wstrb;
  logic start_read_ns;

  always_comb begin
    start_write_ns = 1'b0;
    start_read_ns  = 1'b0;
    start_waddr    = aw_have ? aw_addr : s_awaddr;
    start_wdata    = w_have  ? w_data  : s_wdata;
    start_wstrb    = w_have  ? w_strb  : s_wstrb;
    if (state == IDLE) begin
      if (s_arready && s_arvalid) begin
        start_read_ns = 1'b1;
      end else if ((aw_have || (s_awready && s_awvalid)) &&
                   (w_have  || (s_wready  && s_wvalid))) begin
        start_write_ns = 1'b1;
      end
    end
  end

  always_ff @(posedge clk) begin
    if (!rst_n) begin
      state     <= IDLE;
      aw_have   <= 1'b0;
      w_have    <= 1'b0;
      aw_addr   <= 32'b0;
      w_data    <= 32'b0;
      w_strb    <= 4'b0;
      sel_q     <= 3'b0;
      paddr_q   <= 32'b0;
      pwdata_q  <= 32'b0;
      pstrb_q   <= 4'b0;
      pwrite_q  <= 1'b0;
      bvalid_q  <= 1'b0;
      rvalid_q  <= 1'b0;
      bresp_q   <= 2'b0;
      rresp_q   <= 2'b0;
      rdata_q   <= 32'b0;
    end else begin
      case (state)
        IDLE: begin
          if (start_read_ns) begin
            if (decode(s_araddr) == 3'b000) begin
              rresp_q  <= 2'b11;
              rdata_q  <= 32'b0;
              rvalid_q <= 1'b1;
              state    <= RESP;
            end else begin
              sel_q    <= decode(s_araddr);
              paddr_q  <= local_off(s_araddr);
              pwrite_q <= 1'b0;
              pstrb_q  <= 4'b0;
              pwdata_q <= 32'b0;
              state    <= SETUP;
            end
          end else if (start_write_ns) begin
            aw_have <= 1'b0;
            w_have  <= 1'b0;
            if (decode(start_waddr) == 3'b000) begin
              bresp_q  <= 2'b11;
              bvalid_q <= 1'b1;
              state    <= RESP;
            end else begin
              sel_q    <= decode(start_waddr);
              paddr_q  <= local_off(start_waddr);
              pwrite_q <= 1'b1;
              pwdata_q <= start_wdata;
              pstrb_q  <= start_wstrb;
              state    <= SETUP;
            end
          end else begin
            if (s_awready && s_awvalid) begin
              aw_have <= 1'b1;
              aw_addr <= s_awaddr;
            end
            if (s_wready && s_wvalid) begin
              w_have <= 1'b1;
              w_data <= s_wdata;
              w_strb <= s_wstrb;
            end
          end
        end

        SETUP: begin
          state <= ACCESS;
        end

        ACCESS: begin
          if ((sel_q[0] && pready[0]) || (sel_q[1] && pready[1]) || (sel_q[2] && pready[2])) begin
            logic err;
            err = (sel_q[0] && pslverr[0]) || (sel_q[1] && pslverr[1]) || (sel_q[2] && pslverr[2]);
            if (pwrite_q) begin
              bvalid_q <= 1'b1;
              bresp_q  <= err ? 2'b10 : 2'b00;
            end else begin
              rvalid_q <= 1'b1;
              rresp_q  <= err ? 2'b10 : 2'b00;
              if (sel_q[0]) rdata_q <= prdata[31:0];
              if (sel_q[1]) rdata_q <= prdata[63:32];
              if (sel_q[2]) rdata_q <= prdata[95:64];
            end
            sel_q <= 3'b000;
            state <= RESP;
          end
        end

        RESP: begin
          if (bvalid_q && s_bready) begin
            bvalid_q <= 1'b0;
            state    <= IDLE;
          end else if (rvalid_q && s_rready) begin
            rvalid_q <= 1'b0;
            state    <= IDLE;
          end
        end

        default: state <= IDLE;
      endcase
    end
  end

endmodule