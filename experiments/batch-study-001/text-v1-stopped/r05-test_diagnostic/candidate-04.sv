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

  // Write request buffers
  logic aw_valid_buf, w_valid_buf;
  logic [31:0] aw_addr_buf, w_data_buf;
  logic [3:0] w_strb_buf;

  // Read request buffer
  logic ar_valid_buf;
  logic [31:0] ar_addr_buf;

  // Response pending
  logic bvalid_r, rvalid_r;
  logic [1:0] bresp_r, rresp_r;
  logic [31:0] rdata_r;

  // APB FSM
  typedef enum logic [1:0] {IDLE, SETUP, ACCESS} state_t;
  state_t state;

  // Latched transaction info
  logic cur_write;
  logic [31:0] cur_addr, cur_wdata;
  logic [3:0] cur_strb;

  logic both_wr;
  assign both_wr = aw_valid_buf & w_valid_buf;

  // Accept logic
  assign s_awready = ~aw_valid_buf & ~bvalid_r & (state == IDLE);
  assign s_wready  = ~w_valid_buf  & ~bvalid_r & (state == IDLE);
  assign s_arready = ~ar_valid_buf & ~rvalid_r & (state == IDLE)
                     & ~(s_awready & s_awvalid)
                     & ~(s_wready & s_wvalid)
                     & ~both_wr;

  always_ff @(posedge clk) begin
    if (!rst_n) begin
      aw_valid_buf <= 1'b0;
      w_valid_buf  <= 1'b0;
      ar_valid_buf <= 1'b0;
      aw_addr_buf  <= 32'b0;
      w_data_buf   <= 32'b0;
      w_strb_buf   <= 4'b0;
      ar_addr_buf  <= 32'b0;
      bvalid_r     <= 1'b0;
      rvalid_r     <= 1'b0;
      bresp_r      <= 2'b00;
      rresp_r      <= 2'b00;
      rdata_r      <= 32'b0;
      state        <= IDLE;
      cur_write    <= 1'b0;
      cur_addr     <= 32'b0;
      cur_wdata    <= 32'b0;
      cur_strb     <= 4'b0;
      paddr        <= 32'b0;
      pwdata       <= 32'b0;
      pstrb        <= 4'b0;
      pprot        <= 3'b000;
      psel         <= 1'b0;
      penable      <= 1'b0;
      pwrite       <= 1'b0;
    end else begin
      // Default APB outputs
      psel    <= 1'b0;
      penable <= 1'b0;

      // Accept AW
      if (s_awready && s_awvalid) begin
        aw_valid_buf <= 1'b1;
        aw_addr_buf  <= s_awaddr;
      end
      // Accept W
      if (s_wready && s_wvalid) begin
        w_valid_buf <= 1'b1;
        w_data_buf  <= s_wdata;
        w_strb_buf  <= s_wstrb;
      end
      // Accept AR
      if (s_arready && s_arvalid) begin
        ar_valid_buf <= 1'b1;
        ar_addr_buf  <= s_araddr;
      end

      // Response handshakes
      if (bvalid_r && s_bready)
        bvalid_r <= 1'b0;
      if (rvalid_r && s_rready)
        rvalid_r <= 1'b0;

      case (state)
        IDLE: begin
          if (both_wr && !bvalid_r) begin
            // Start write
            cur_write <= 1'b1;
            cur_addr  <= aw_addr_buf;
            cur_wdata <= w_data_buf;
            cur_strb  <= w_strb_buf;
            paddr     <= aw_addr_buf;
            pwdata    <= w_data_buf;
            pstrb     <= w_strb_buf;
            pwrite    <= 1'b1;
            pprot     <= 3'b000;
            psel      <= 1'b1;
            penable   <= 1'b0;
            state     <= SETUP;
            aw_valid_buf <= 1'b0;
            w_valid_buf  <= 1'b0;
          end else if (ar_valid_buf && !rvalid_r) begin
            cur_write <= 1'b0;
            cur_addr  <= ar_addr_buf;
            paddr     <= ar_addr_buf;
            pwdata    <= 32'b0;
            pstrb     <= 4'b0;
            pwrite    <= 1'b0;
            pprot     <= 3'b000;
            psel      <= 1'b1;
            penable   <= 1'b0;
            state     <= SETUP;
            ar_valid_buf <= 1'b0;
          end
        end

        SETUP: begin
          psel    <= 1'b1;
          penable <= 1'b1;
          // keep stable
          paddr   <= cur_addr;
          pwrite  <= cur_write;
          pprot   <= 3'b000;
          if (cur_write) begin
            pwdata <= cur_wdata;
            pstrb  <= cur_strb;
          end else begin
            pwdata <= 32'b0;
            pstrb  <= 4'b0;
          end
          state <= ACCESS;
        end

        ACCESS: begin
          psel    <= 1'b1;
          penable <= 1'b1;
          paddr   <= cur_addr;
          pwrite  <= cur_write;
          pprot   <= 3'b000;
          if (cur_write) begin
            pwdata <= cur_wdata;
            pstrb  <= cur_strb;
          end else begin
            pwdata <= 32'b0;
            pstrb  <= 4'b0;
          end
          if (pready) begin
            if (cur_write) begin
              bvalid_r <= 1'b1;
              bresp_r  <= pslverr ? 2'b10 : 2'b00;
            end else begin
              rvalid_r <= 1'b1;
              rresp_r  <= pslverr ? 2'b10 : 2'b00;
              rdata_r  <= prdata;
            end
            state <= IDLE;
          end else begin
            state <= ACCESS;
          end
        end

        default: state <= IDLE;
      endcase
    end
  end

  assign s_bvalid = bvalid_r;
  assign s_bresp  = bresp_r;
  assign s_rvalid = rvalid_r;
  assign s_rresp  = rresp_r;
  assign s_rdata  = rdata_r;

endmodule
