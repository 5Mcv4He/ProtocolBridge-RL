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

  // ---- decode helpers (combinational) ----
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

  // ---- state ----
  typedef enum logic [2:0] {
    IDLE,
    WR_WAIT,     // have partial write, waiting for other half
    SETUP,
    ACCESS,
    RESP
  } state_t;

  state_t state;

  // write buffers
  logic        aw_have, w_have;
  logic [31:0] aw_addr;
  logic [31:0] w_data;
  logic [3:0]  w_strb;

  // registered APB payload (stable through setup/access)
  logic [2:0]  sel_q;
  logic [31:0] paddr_q, pwdata_q;
  logic [3:0]  pstrb_q;
  logic        pwrite_q;

  // response pending
  logic        bvalid_q, rvalid_q;
  logic [1:0]  bresp_q, rresp_q;
  logic [31:0] rdata_q;

  // unmapped request flag
  logic        resp_is_unmapped;

  // determine mapped target for the pending/started request
  logic [2:0]  cur_sel;
  logic        cur_is_write;
  logic        cur_unmapped;

  always_comb begin
    // default
    s_awready = 1'b0;
    s_wready  = 1'b0;
    s_arready = 1'b0;

    if (state == IDLE || state == WR_WAIT) begin
      s_awready = !aw_have;
      s_wready  = !w_have;
    end
    if (state == IDLE && !aw_have && !w_have) begin
      s_arready = 1'b1;
    end
  end

  always_comb begin
    psel    = sel_q;
    penable = (state == ACCESS);
    paddr   = paddr_q;
    pwrite  = pwrite_q;
    pwdata  = pwdata_q;
    pstrb   = pstrb_q;
    pprot   = 3'b000;
  end

  always_comb begin
    s_bvalid = bvalid_q;
    s_bresp  = bresp_q;
    s_rvalid = rvalid_q;
    s_rdata  = rdata_q;
    s_rresp  = rresp_q;
  end

  always_ff @(posedge clk) begin
    if (!rst_n) begin
      state           <= IDLE;
      aw_have         <= 1'b0;
      w_have          <= 1'b0;
      aw_addr         <= 32'b0;
      w_data          <= 32'b0;
      w_strb          <= 4'b0;
      sel_q           <= 3'b0;
      paddr_q         <= 32'b0;
      pwdata_q        <= 32'b0;
      pstrb_q         <= 4'b0;
      pwrite_q        <= 1'b0;
      bvalid_q        <= 1'b0;
      rvalid_q        <= 1'b0;
      bresp_q         <= 2'b0;
      rresp_q         <= 2'b0;
      rdata_q         <= 32'b0;
      resp_is_unmapped<= 1'b0;
    end else begin
      // accept new half-writes
      if (s_awready && s_awvalid && !aw_have) begin
        aw_have <= 1'b1;
        aw_addr <= s_awaddr;
      end
      if (s_wready && s_wvalid && !w_have) begin
        w_have <= 1'b1;
        w_data <= s_wdata;
        w_strb <= s_wstrb;
      end

      case (state)
        IDLE: begin
          // accept read
          if (s_arready && s_arvalid) begin
            sel_q    <= decode(s_araddr);
            paddr_q  <= s_araddr;
            // determine mapped or not
            if (decode(s_araddr) == 3'b000) begin
              // unmapped read: respond DECERR
              sel_q    <= 3'b000;
              paddr_q  <= local_off(s_araddr);
              rresp_q  <= 2'b11;
              rdata_q  <= 32'b0;
              rvalid_q <= 1'b1;
              // stay IDLE, response driven from registers
            end else begin
              paddr_q  <= local_off(s_araddr);
              pwrite_q <= 1'b0;
              pstrb_q  <= 4'b0;
              pwdata_q <= 32'b0;
              resp_is_unmapped <= 1'b0;
              state    <= SETUP;
            end
          end else if (aw_have && w_have) begin
            // both halves present, start write
            if (decode(aw_addr) == 3'b000) begin
              // unmapped write: respond DECERR
              sel_q    <= 3'b000;
              bresp_q  <= 2'b11;
              bvalid_q <= 1'b1;
              aw_have  <= 1'b0;
              w_have   <= 1'b0;
              // stay IDLE
            end else begin
              sel_q    <= decode(aw_addr);
              paddr_q  <= local_off(aw_addr);
              pwrite_q <= 1'b1;
              pwdata_q <= w_data;
              pstrb_q  <= w_strb;
              aw_have  <= 1'b0;
              w_have   <= 1'b0;
              state    <= SETUP;
            end
          end
        end

        WR_WAIT: begin
          if (aw_have && w_have) begin
            if (decode(aw_addr) == 3'b000) begin
              sel_q    <= 3'b000;
              bresp_q  <= 2'b11;
              bvalid_q <= 1'b1;
              aw_have  <= 1'b0;
              w_have   <= 1'b0;
              state    <= IDLE;
            end else begin
              sel_q    <= decode(aw_addr);
              paddr_q  <= local_off(aw_addr);
              pwrite_q <= 1'b1;
              pwdata_q <= w_data;
              pstrb_q  <= w_strb;
              aw_have  <= 1'b0;
              w_have   <= 1'b0;
              state    <= SETUP;
            end
          end
        end

        SETUP: begin
          state <= ACCESS;
        end

        ACCESS: begin
          if (|sel_q && pready[0] || |sel_q && pready[1] || |sel_q && pready[2]) begin
            // selected target ready
            logic err;
            err = 1'b0;
            if (sel_q[0]) err = pslverr[0];
            if (sel_q[1]) err = pslverr[1];
            if (sel_q[2]) err = pslverr[2];
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
            state <= RESP;
          end
        end

        RESP: begin
          sel_q <= 3'b000;
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

      // when in IDLE and unmapped responses still pending, hold until accepted
      if (state == IDLE) begin
        if (bvalid_q && s_bready) bvalid_q <= 1'b0;
        if (rvalid_q && s_rready) rvalid_q <= 1'b0;
        // if response pending, don't accept new (handled by arready gating?)
      end
    end
  end

endmodule