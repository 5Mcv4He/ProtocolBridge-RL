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

  state_t state, nstate;

  logic aw_full, w_full, is_write;
  logic [31:0] aw_addr, w_data;
  logic [3:0] w_strb;
  logic [31:0] ar_addr;
  logic [31:0] rdata_r;
  logic bresp_r, rresp_r;

  // Request acceptance
  assign s_awready = (state == IDLE) && !aw_full;
  assign s_wready  = (state == IDLE) && !w_full;
  assign s_arready = (state == IDLE) && !aw_full && !w_full && !s_awvalid && !s_wvalid;

  assign s_bvalid = (state == RESP_B);
  assign s_bresp  = bresp_r ? 2'b10 : 2'b00;
  assign s_rvalid = (state == RESP_R);
  assign s_rdata  = rdata_r;
  assign s_rresp  = rresp_r ? 2'b10 : 2'b00;

  assign paddr  = is_write ? aw_addr : ar_addr;
  assign pwdata = w_data;
  assign pstrb  = is_write ? w_strb : 4'b0000;
  assign pprot  = 3'b000;
  assign pwrite = is_write;
  assign psel   = (state == SETUP) || (state == ACCESS);
  assign penable = (state == ACCESS);

  always_comb begin
    nstate = state;
    case (state)
      IDLE: begin
        if (aw_full && w_full)
          nstate = SETUP;
        else if (ar_addr != 32'b0) // placeholder; replaced below
          nstate = IDLE;
      end
      SETUP: nstate = ACCESS;
      ACCESS: if (pready) nstate = is_write ? RESP_B : RESP_R;
      RESP_B: if (s_bready) nstate = IDLE;
      RESP_R: if (s_rready) nstate = IDLE;
      default: nstate = IDLE;
    endcase
  end

endmodule
