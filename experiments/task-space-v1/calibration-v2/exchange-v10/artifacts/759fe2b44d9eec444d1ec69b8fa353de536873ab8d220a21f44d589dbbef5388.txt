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

  localparam [2:0] IDLE    = 3'd0,
                   SETUP   = 3'd1,
                   ACCESS  = 3'd2,
                   WB_RESP = 3'd3,
                   RD_RESP = 3'd4;

  logic [2:0] state;

  logic aw_have, w_have;
  logic [31:0] aw_addr, w_data;
  logic [3:0] w_strb;

  logic [31:0] a_addr, a_wdata;
  logic [3:0]  a_strb;
  logic [2:0]  a_sel;
  logic        a_write;

  logic [1:0]  b_resp_reg, r_resp_reg;
  logic [31:0] r_data_reg;

  logic [1:0]  dec_tgt; logic dec_valid; logic [31:0] dec_off;
  always_comb begin
    dec_valid = 1'b1;
    dec_off   = 32'h0;
    dec_tgt   = 2'd0;
    if (aw_addr <= 32'h0001_0fff && aw_addr >= 32'h0001_0000) begin
      dec_tgt = 2'd0; dec_off = aw_addr - 32'h0001_0000;
    end else if (aw_addr <= 32'h0001_2fff && aw_addr >= 32'h0001_1000) begin
      dec_tgt = 2'd1; dec_off = aw_addr - 32'h0001_1000;
    end else if (aw_addr <= 32'h4001_2fff && aw_addr >= 32'h4001_0000) begin
      dec_tgt = 2'd2; dec_off = aw_addr - 32'h4001_0000;
    end else begin
      dec_tgt = 2'd0; dec_valid = 1'b0; dec_off = 32'h0;
    end
  end

  logic [1:0]  rd_tgt; logic rd_valid; logic [31:0] rd_off;
  always_comb begin
    rd_valid = 1'b1;
    rd_off   = 32'h0;
    rd_tgt   = 2'd0;
    if (s_araddr <= 32'h0001_0fff && s_araddr >= 32'h0001_0000) begin
      rd_tgt = 2'd0; rd_off = s_araddr - 32'h0001_0000;
    end else if (s_araddr <= 32'h0001_2fff && s_araddr >= 32'h0001_1000) begin
      rd_tgt = 2'd1; rd_off = s_araddr - 32'h0001_1000;
    end else if (s_araddr <= 32'h4001_2fff && s_araddr >= 32'h4001_0000) begin
      rd_tgt = 2'd2; rd_off = s_araddr - 32'h4001_0000;
    end else begin
      rd_tgt = 2'd0; rd_valid = 1'b0; rd_off = 32'h0;
    end
  end

  // AXI accept
  logic idle_like, take_ar, take_aw, take_w;
  assign idle_like = (state == IDLE);
  assign take_ar = s_arvalid && idle_like && !aw_have && !w_have && !s_awvalid && !s_wvalid;
  assign take_aw = s_awvalid && idle_like && !aw_have;
  assign take_w  = s_wvalid && idle_like && !w_have && (aw_have || s_awvalid);

  assign s_awready = idle_like && !aw_have;
  assign s_wready  = idle_like && !w_have && (aw_have || s_awvalid);
  assign s_arready = idle_like && !aw_have && !w_have && !s_awvalid && !s_wvalid;

  assign s_bvalid = (state == WB_RESP);
  assign s_bresp  = b_resp_reg;
  assign s_rvalid = (state == RD_RESP);
  assign s_rdata  = r_data_reg;
  assign s_rresp  = r_resp_reg;

  assign psel    = (state == SETUP || state == ACCESS) ? a_sel : 3'b000;
  assign penable = (state == ACCESS);
  assign paddr   = ((state == SETUP) || (state == ACCESS)) ? a_addr : 32'h0;
  assign pwrite  = ((state == SETUP) || (state == ACCESS)) ? a_write : 1'b0;
  assign pwdata  = ((state == SETUP) || (state == ACCESS)) ? a_wdata : 32'h0;
  assign pstrb   = ((state == SETUP) || (state == ACCESS)) ? a_strb : 4'b0;
  assign pprot   = 3'b000;

  logic tgt_pre, tgt_slv;
  always_comb begin
    tgt_pre = 1'b0; tgt_slv = 1'b0;
    if (a_sel[0]) begin tgt_pre = pready[0]; tgt_slv = pslverr[0]; end
    else if (a_sel[1]) begin tgt_pre = pready[1]; tgt_slv = pslverr[1]; end
    else if (a_sel[2]) begin tgt_pre = pready[2]; tgt_slv = pslverr[2]; end
  end

  logic [31:0] sel_rdata;
  always_comb begin
    sel_rdata = 32'h0;
    if (a_sel[0]) sel_rdata = prdata[31:0];
    else if (a_sel[1]) sel_rdata = prdata[63:32];
    else if (a_sel[2]) sel_rdata = prdata[95:64];
  end

  logic wr_issue;
  logic [31:0] wr_addr;
  assign wr_addr = aw_have ? aw_addr : s_awaddr;
  assign wr_issue = idle_like && !take_ar &&
                    ((aw_have && w_have) || (aw_have && take_w) ||
                     (w_have && take_aw) || (take_aw && take_w));

  always_ff @(posedge clk) begin
    if (!rst_n) begin
      state      <= IDLE;
      aw_have    <= 1'b0;
      w_have     <= 1'b0;
      aw_addr    <= 32'h0;
      w_data     <= 32'h0;
      w_strb     <= 4'h0;
      a_addr     <= 32'h0;
      a_wdata    <= 32'h0;
      a_strb     <= 4'h0;
      a_sel      <= 3'b000;
      a_write    <= 1'b0;
      b_resp_reg <= 2'b00;
      r_resp_reg <= 2'b00;
      r_data_reg <= 32'h0;
    end else begin
      case (state)
        IDLE: begin
          if (take_ar) begin
            a_addr  <= rd_off;
            a_write <= 1'b0;
            a_wdata <= 32'h0;
            a_strb  <= 4'h0;
            if (rd_valid) begin
              if (rd_tgt == 2'd0) a_sel <= 3'b001;
              else if (rd_tgt == 2'd1) a_sel <= 3'b010;
              else a_sel <= 3'b100;
              state <= SETUP;
            end else begin
              a_sel <= 3'b000;
              r_data_reg <= 32'h0;
              r_resp_reg <= 2'b11;
              state <= RD_RESP;
            end
          end else if (wr_issue) begin
            a_wdata <= w_have ? w_data : s_wdata;
            a_strb  <= w_have ? w_strb : s_wstrb;
            a_write <= 1'b1;
            aw_have <= 1'b0;
            w_have  <= 1'b0;
            if (dec_valid) begin
              a_addr <= dec_off;
              if (dec_tgt == 2'd0) a_sel <= 3'b001;
              else if (dec_tgt == 2'd1) a_sel <= 3'b010;
              else a_sel <= 3'b100;
              state <= SETUP;
            end else begin
              a_sel <= 3'b000;
              b_resp_reg <= 2'b11;
              state <= WB_RESP;
            end
          end else begin
            if (take_aw) begin
              aw_have <= 1'b1;
              aw_addr <= s_awaddr;
            end
            if (take_w) begin
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
          if (tgt_pre) begin
            if (a_write) begin
              b_resp_reg <= tgt_slv ? 2'b10 : 2'b00;
              state <= WB_RESP;
            end else begin
              r_data_reg <= sel_rdata;
              r_resp_reg <= tgt_slv ? 2'b10 : 2'b00;
              state <= RD_RESP;
            end
          end
        end
        WB_RESP: begin
          if (s_bready) begin
            aw_have <= 1'b0;
            w_have  <= 1'b0;
            state   <= IDLE;
          end
        end
        RD_RESP: begin
          if (s_rready) begin
            aw_have <= 1'b0;
            w_have  <= 1'b0;
            state   <= IDLE;
          end
        end
        default: state <= IDLE;
      endcase
    end
  end

endmodule
