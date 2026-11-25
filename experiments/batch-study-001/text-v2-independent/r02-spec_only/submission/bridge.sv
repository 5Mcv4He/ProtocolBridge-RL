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

  typedef enum logic [2:0] {
    IDLE, SETUP, ACCESS, RESP_B, RESP_R
  } state_t;

  state_t state;

  logic aw_full, w_full, ar_full, is_write;
  logic [31:0] aw_addr, w_data, ar_addr;
  logic [3:0] w_strb;
  logic [31:0] rdata_r;
  logic [1:0] bresp_r, rresp_r;

  assign s_awready = (state == IDLE) && !aw_full;
  assign s_wready  = (state == IDLE) && !w_full;
  assign s_arready = (state == IDLE) && !ar_full && !aw_full && !w_full;

  assign s_bvalid = (state == RESP_B);
  assign s_bresp  = bresp_r;
  assign s_rvalid = (state == RESP_R);
  assign s_rdata  = rdata_r;
  assign s_rresp  = rresp_r;

  assign paddr   = is_write ? aw_addr : ar_addr;
  assign pwdata  = w_data;
  assign pstrb   = is_write ? w_strb : 4'b0000;
  assign pprot   = 3'b000;
  assign pwrite  = is_write;
  assign psel    = (state == SETUP) || (state == ACCESS);
  assign penable = (state == ACCESS);

  always_ff @(posedge clk) begin
    if (!rst_n) begin
      state   <= IDLE;
      aw_full <= 1'b0;
      w_full  <= 1'b0;
      ar_full <= 1'b0;
      is_write <= 1'b0;
      aw_addr <= 32'b0;
      w_data  <= 32'b0;
      w_strb  <= 4'b0;
      ar_addr <= 32'b0;
      rdata_r <= 32'b0;
      bresp_r <= 2'b00;
      rresp_r <= 2'b00;
    end else begin
      case (state)
        IDLE: begin
          if (s_awvalid && s_awready) begin
            aw_full <= 1'b1;
            aw_addr <= s_awaddr;
          end
          if (s_wvalid && s_wready) begin
            w_full <= 1'b1;
            w_data <= s_wdata;
            w_strb <= s_wstrb;
          end
          if (s_arvalid && s_arready) begin
            ar_full <= 1'b1;
            ar_addr <= s_araddr;
          end

          if (ar_full) begin
            is_write <= 1'b0;
            state    <= SETUP;
            ar_full  <= 1'b0;
          end else if (aw_full && w_full) begin
            is_write <= 1'b1;
            state    <= SETUP;
          end
        end
        SETUP: begin
          state <= ACCESS;
        end
        ACCESS: begin
          if (pready) begin
            if (is_write) begin
              bresp_r <= pslverr ? 2'b10 : 2'b00;
              state   <= RESP_B;
            end else begin
              rdata_r <= prdata;
              rresp_r <= pslverr ? 2'b10 : 2'b00;
              state   <= RESP_R;
            end
          end
        end
        RESP_B: begin
          if (s_bready) begin
            aw_full <= 1'b0;
            w_full  <= 1'b0;
            state   <= IDLE;
          end
        end
        RESP_R: begin
          if (s_rready) begin
            state <= IDLE;
          end
        end
        default: state <= IDLE;
      endcase
    end
  end

endmodule
