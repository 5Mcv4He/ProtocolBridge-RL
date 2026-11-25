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

  // State encoding
  localparam IDLE   = 2'd0;  // no outstanding write halves, no APB, no response
  localparam WRITE  = 2'd1;  // collecting AW/W
  localparam APBSET = 2'd2;  // APB setup cycle
  localparam APBACC = 2'd3;  // APB access

  logic [1:0] state;

  // Buffered write halves
  logic aw_have, w_have;
  logic [31:0] aw_addr_buf;
  logic [31:0] w_data_buf;
  logic [3:0]  w_strb_buf;

  // Active APB command
  logic        is_write;
  logic [31:0] cmd_addr;
  logic [31:0] cmd_wdata;
  logic [3:0]  cmd_strb;

  // Response registers
  logic        bvalid_r, rvalid_r;
  logic [31:0] rdata_r;

  assign pprot = 3'b000;

  // Input ready generation
  assign s_awready = rst_n && (state == IDLE) && (s_awvalid && !aw_have) ;
  // More simply: accept whenever idle and we do not already have it
  // (we recompute below - see combinational overrides)

  // We need READY not dependent on VALID. Use separate signals.
  logic aw_accept, w_accept, ar_accept;

  always_comb begin
    aw_accept = 1'b0;
    w_accept  = 1'b0;
    ar_accept = 1'b0;
    if (state == IDLE) begin
      // can accept write halves and AR; AR only if no write halves present
      if (!aw_have && !(w_have)) begin
        if (s_awvalid) aw_accept = 1'b1;
        else if (s_arvalid && !s_awvalid && !s_wvalid) ar_accept = 1'b1;
      end
      if (!w_have && !(s_awvalid && !aw_have && s_arvalid && !s_wvalid)) begin
        if (s_wvalid) w_accept = 1'b1;
      end
    end else if (state == WRITE) begin
      if (!aw_have && s_awvalid) aw_accept = 1'b1;
      if (!w_have && s_wvalid) w_accept = 1'b1;
    end
  end

  assign s_awready = aw_accept;
  assign s_wready  = w_accept;
  assign s_arready = ar_accept;

  always_ff @(posedge clk) begin
    if (!rst_n) begin
      state     <= IDLE;
      aw_have   <= 1'b0;
      w_have    <= 1'b0;
      aw_addr_buf <= '0;
      w_data_buf  <= '0;
      w_strb_buf  <= '0;
      is_write  <= 1'b0;
      cmd_addr  <= '0;
      cmd_wdata <= '0;
      cmd_strb  <= '0;
      bvalid_r  <= 1'b0;
      rvalid_r  <= 1'b0;
      rdata_r   <= '0;
      psel      <= 1'b0;
      penable   <= 1'b0;
      pwrite    <= 1'b0;
      paddr     <= '0;
      pwdata    <= '0;
      pstrb     <= '0;
    end else begin
      case (state)
        IDLE: begin
          psel    <= 1'b0;
          penable <= 1'b0;
          // capture write halves
          if (aw_accept) begin
            aw_have     <= 1'b1;
            aw_addr_buf <= s_awaddr;
          end
          if (w_accept) begin
            w_have     <= 1'b1;
            w_data_buf <= s_wdata;
            w_strb_buf <= s_wstrb;
          end
          // start read
          if (ar_accept) begin
            is_write  <= 1'b0;
            cmd_addr  <= s_araddr;
            cmd_wdata <= '0;
            cmd_strb  <= '0;
            psel      <= 1'b1;
            penable   <= 1'b0;
            pwrite    <= 1'b0;
            paddr     <= s_araddr;
            pwdata    <= '0;
            pstrb     <= '0;
            state     <= APBSET;
          end else if ((aw_have || aw_accept) && (w_have || w_accept)) begin
            // both halves will be available next cycle -> launch write
            is_write  <= 1'b1;
            cmd_addr  <= aw_accept ? s_awaddr : aw_addr_buf;
            cmd_wdata <= w_accept  ? s_wdata  : w_data_buf;
            cmd_strb  <= w_accept  ? s_wstrb  : w_strb_buf;
            psel      <= 1'b1;
            penable   <= 1'b0;
            pwrite    <= 1'b1;
            paddr     <= aw_accept ? s_awaddr : aw_addr_buf;
            pwdata    <= w_accept  ? s_wdata  : w_data_buf;
            pstrb     <= w_accept  ? s_wstrb  : w_strb_buf;
            state     <= APBSET;
          end else if (aw_accept || w_accept) begin
            state <= WRITE;
          end
        end
        WRITE: begin
          psel    <= 1'b0;
          penable <= 1'b0;
          if (aw_accept) begin
            aw_have     <= 1'b1;
            aw_addr_buf <= s_awaddr;
          end
          if (w_accept) begin
            w_have     <= 1'b1;
            w_data_buf <= s_wdata;
            w_strb_buf <= s_wstrb;
          end
          if ((aw_have || aw_accept) && (w_have || w_accept)) begin
            is_write  <= 1'b1;
            cmd_addr  <= aw_accept ? s_awaddr : aw_addr_buf;
            cmd_wdata <= w_accept  ? s_wdata  : w_data_buf;
            cmd_strb  <= w_accept  ? s_wstrb  : w_strb_buf;
            psel      <= 1'b1;
            penable   <= 1'b0;
            pwrite    <= 1'b1;
            paddr     <= aw_accept ? s_awaddr : aw_addr_buf;
            pwdata    <= w_accept  ? s_wdata  : w_data_buf;
            pstrb     <= w_accept  ? s_wstrb  : w_strb_buf;
            state     <= APBSET;
          end
        end
        APBSET: begin
          psel    <= 1'b1;
          penable <= 1'b1;
          pwrite  <= is_write;
          paddr   <= cmd_addr;
          pwdata  <= is_write ? cmd_wdata : '0;
          pstrb   <= is_write ? cmd_strb  : '0;
          state   <= APBACC;
        end
        APBACC: begin
          if (pready) begin
            penable <= 1'b0;
            psel    <= 1'b0;
            if (is_write) begin
              bvalid_r <= 1'b1;
              s_bresp  <= pslverr ? 2'b10 : 2'b00;
              // clear write buffers
              aw_have  <= 1'b0;
              w_have   <= 1'b0;
            end else begin
              rvalid_r <= 1'b1;
              rdata_r  <= prdata;
              s_rresp  <= pslverr ? 2'b10 : 2'b00;
            end
            state <= IDLE;
          end
        end
      endcase

      // Response handshakes
      if (bvalid_r && s_bready) begin
        bvalid_r <= 1'b0;
      end
      if (rvalid_r && s_rready) begin
        rvalid_r <= 1'b0;
      end
    end
  end

  assign s_bvalid = bvalid_r;
  assign s_rvalid = rvalid_r;
  assign s_rdata  = rdata_r;

endmodule
