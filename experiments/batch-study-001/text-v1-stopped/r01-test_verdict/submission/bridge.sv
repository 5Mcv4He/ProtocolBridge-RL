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

  localparam IDLE   = 2'd0;
  localparam WRITE  = 2'd1;
  localparam APBSET = 2'd2;
  localparam APBACC = 2'd3;

  logic [1:0] state;

  logic aw_have, w_have;
  logic [31:0] aw_addr_buf;
  logic [31:0] w_data_buf;
  logic [3:0]  w_strb_buf;

  logic        is_write;
  logic [31:0] cmd_addr;
  logic [31:0] cmd_wdata;
  logic [3:0]  cmd_strb;

  logic        bvalid_r, rvalid_r;
  logic [1:0]  bresp_r, rresp_r;
  logic [31:0] rdata_r;

  assign pprot    = 3'b000;
  assign s_bvalid = bvalid_r;
  assign s_rvalid = rvalid_r;
  assign s_bresp  = bresp_r;
  assign s_rresp  = rresp_r;
  assign s_rdata  = rdata_r;

  // Ready: can accept when in IDLE or WRITE and the half is not yet held.
  // AR only accepted in IDLE.
  logic bus_idle;
  assign bus_idle = (state == IDLE);

  assign s_awready = ((state == IDLE) || (state == WRITE)) && !aw_have;
  assign s_wready  = ((state == IDLE) || (state == WRITE)) && !w_have;
  assign s_arready = bus_idle && !aw_have && !w_have;

  // Combinational next-half visibility
  logic aw_next, w_next;
  assign aw_next = aw_have | (s_awvalid & s_awready);
  assign w_next  = w_have  | (s_wvalid  & s_wready);
  logic ar_next;
  assign ar_next = s_arvalid & s_arready;

  always_ff @(posedge clk) begin
    if (!rst_n) begin
      state       <= IDLE;
      aw_have     <= 1'b0;
      w_have      <= 1'b0;
      aw_addr_buf <= '0;
      w_data_buf  <= '0;
      w_strb_buf  <= '0;
      is_write    <= 1'b0;
      cmd_addr    <= '0;
      cmd_wdata   <= '0;
      cmd_strb    <= '0;
      bvalid_r    <= 1'b0;
      rvalid_r    <= 1'b0;
      bresp_r     <= 2'b00;
      rresp_r     <= 2'b00;
      rdata_r     <= '0;
      psel        <= 1'b0;
      penable     <= 1'b0;
      pwrite      <= 1'b0;
      paddr       <= '0;
      pwdata      <= '0;
      pstrb       <= '0;
    end else begin
      case (state)
        IDLE: begin
          psel    <= 1'b0;
          penable <= 1'b0;

          if (ar_next) begin
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
          end else if (aw_next && w_next) begin
            if (s_awvalid & s_awready) begin
              cmd_addr <= s_awaddr;
              paddr    <= s_awaddr;
            end else begin
              cmd_addr <= aw_addr_buf;
              paddr    <= aw_addr_buf;
            end
            if (s_wvalid & s_wready) begin
              cmd_wdata <= s_wdata;
              cmd_strb  <= s_wstrb;
              pwdata    <= s_wdata;
              pstrb     <= s_wstrb;
            end else begin
              cmd_wdata <= w_data_buf;
              cmd_strb  <= w_strb_buf;
              pwdata    <= w_data_buf;
              pstrb     <= w_strb_buf;
            end
            is_write <= 1'b1;
            psel     <= 1'b1;
            penable  <= 1'b0;
            pwrite   <= 1'b1;
            state    <= APBSET;
          end else if (s_awvalid & s_awready) begin
            aw_have     <= 1'b1;
            aw_addr_buf <= s_awaddr;
            state       <= WRITE;
          end else if (s_wvalid & s_wready) begin
            w_have     <= 1'b1;
            w_data_buf <= s_wdata;
            w_strb_buf <= s_wstrb;
            state      <= WRITE;
          end
        end
        WRITE: begin
          psel    <= 1'b0;
          penable <= 1'b0;

          if (!aw_have && s_awvalid & s_awready) begin
            aw_have     <= 1'b1;
            aw_addr_buf <= s_awaddr;
          end
          if (!w_have && s_wvalid & s_wready) begin
            w_have     <= 1'b1;
            w_data_buf <= s_wdata;
            w_strb_buf <= s_wstrb;
          end

          if (aw_next && w_next) begin
            if (s_awvalid & s_awready) begin
              cmd_addr <= s_awaddr;
              paddr    <= s_awaddr;
            end else begin
              cmd_addr <= aw_addr_buf;
              paddr    <= aw_addr_buf;
            end
            if (s_wvalid & s_wready) begin
              cmd_wdata <= s_wdata;
              cmd_strb  <= s_wstrb;
              pwdata    <= s_wdata;
              pstrb     <= s_wstrb;
            end else begin
              cmd_wdata <= w_data_buf;
              cmd_strb  <= w_strb_buf;
              pwdata    <= w_data_buf;
              pstrb     <= w_strb_buf;
            end
            is_write <= 1'b1;
            psel     <= 1'b1;
            penable  <= 1'b0;
            pwrite   <= 1'b1;
            state    <= APBSET;
          end
        end
        APBSET: begin
          // setup was driven in prior cycle; now assert penable
          psel    <= 1'b1;
          penable <= 1'b1;
          if (pready) begin
            penable <= 1'b0;
            psel    <= 1'b0;
            if (is_write) begin
              bvalid_r <= 1'b1;
              bresp_r  <= pslverr ? 2'b10 : 2'b00;
              aw_have  <= 1'b0;
              w_have   <= 1'b0;
            end else begin
              rvalid_r <= 1'b1;
              rresp_r  <= pslverr ? 2'b10 : 2'b00;
              rdata_r  <= prdata;
            end
            state <= IDLE;
          end else begin
            state <= APBACC;
          end
        end
        APBACC: begin
          psel    <= 1'b1;
          penable <= 1'b1;
          if (pready) begin
            penable <= 1'b0;
            psel    <= 1'b0;
            if (is_write) begin
              bvalid_r <= 1'b1;
              bresp_r  <= pslverr ? 2'b10 : 2'b00;
              aw_have  <= 1'b0;
              w_have   <= 1'b0;
            end else begin
              rvalid_r <= 1'b1;
              rresp_r  <= pslverr ? 2'b10 : 2'b00;
              rdata_r  <= prdata;
            end
            state <= IDLE;
          end
        end
      endcase

      if (bvalid_r && s_bready) bvalid_r <= 1'b0;
      if (rvalid_r && s_rready) rvalid_r <= 1'b0;
    end
  end

endmodule
