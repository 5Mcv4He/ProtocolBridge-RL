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
  logic have_aw, have_w;
  logic [31:0] awaddr_q, wdata_q;
  logic [3:0] wstrb_q;
  logic has_ar;
  logic [31:0] araddr_q;
  logic bpend, rpend;
  logic [1:0] bresp_q, rresp_q;
  logic [31:0] rdata_q;
  logic active; // APB transaction in progress
  logic access; // in access phase
  logic cur_write;
  logic [31:0] addr_q, wdata_hold;
  logic [3:0] strb_hold;

  assign s_awready = !have_aw && !active && !bpend && !rpend && !has_ar && !cur_write;
  assign s_wready  = !have_w && !active && !bpend && !rpend && !has_ar && !cur_write;
  assign s_arready = !has_ar && !active && !bpend && !rpend && !have_aw && !have_w;

  assign s_bvalid = bpend;
  assign s_bresp = bresp_q;
  assign s_rvalid = rpend;
  assign s_rdata = rdata_q;
  assign s_rresp = rresp_q;

  assign pprot = 3'b000;
  assign psel = active;
  assign penable = active && access;
  assign pwrite = cur_write;
  assign paddr = addr_q;
  assign pwdata = cur_write ? wdata_hold : 32'b0;
  assign pstrb = cur_write ? strb_hold : 4'b0000;

  logic do_launch;
  logic do_complete;

  assign do_launch = active && !access;
  assign do_complete = active && access && pready;

  always_ff @(posedge clk) begin
    if (!rst_n) begin
      have_aw <= 1'b0;
      have_w  <= 1'b0;
      has_ar  <= 1'b0;
      awaddr_q <= '0;
      wdata_q  <= '0;
      wstrb_q  <= '0;
      araddr_q <= '0;
      bpend <= 1'b0;
      rpend <= 1'b0;
      bresp_q <= 2'b00;
      rresp_q <= 2'b00;
      rdata_q <= '0;
      active <= 1'b0;
      access <= 1'b0;
      cur_write <= 1'b0;
      addr_q <= '0;
      wdata_hold <= '0;
      strb_hold <= '0;
    end else begin
      // AXI write half capture
      if (s_awready && s_awvalid) begin
        have_aw <= 1'b1;
        awaddr_q <= s_awaddr;
      end
      if (s_wready && s_wvalid) begin
        have_w <= 1'b1;
        wdata_q <= s_wdata;
        wstrb_q <= s_wstrb;
      end
      if (s_arready && s_arvalid) begin
        has_ar <= 1'b1;
        araddr_q <= s_araddr;
      end

      // response handshakes
      if (bpend && s_bready) bpend <= 1'b0;
      if (rpend && s_rready) rpend <= 1'b0;

      // APB progression
      if (do_complete) begin
        active <= 1'b0;
        access <= 1'b0;
        if (cur_write) begin
          bpend <= 1'b1;
          bresp_q <= pslverr ? 2'b10 : 2'b00;
        end else begin
          rpend <= 1'b1;
          rdata_q <= prdata;
          rresp_q <= pslverr ? 2'b10 : 2'b00;
        end
      end else if (do_launch) begin
        access <= 1'b1;
      end

      // launch new APB transaction
      if (!active && !bpend && !rpend) begin
        if (have_aw && have_w) begin
          active <= 1'b1;
          access <= 1'b0;
          cur_write <= 1'b1;
          addr_q <= awaddr_q;
          wdata_hold <= wdata_q;
          strb_hold <= wstrb_q;
          have_aw <= 1'b0;
          have_w <= 1'b0;
          // note: aw/w captures for a new half can't occur this cycle (ready low while active)
        end else if (has_ar && !have_aw && !have_w) begin
          active <= 1'b1;
          access <= 1'b0;
          cur_write <= 1'b0;
          addr_q <= araddr_q;
          has_ar <= 1'b0;
        end else if (has_ar) begin
          active <= 1'b1;
          access <= 1'b0;
          cur_write <= 1'b0;
          addr_q <= araddr_q;
          has_ar <= 1'b0;
        end else if (have_aw && have_w) begin
          active <= 1'b1;
          access <= 1'b0;
          cur_write <= 1'b1;
          addr_q <= awaddr_q;
          wdata_hold <= wdata_q;
          strb_hold <= wstrb_q;
          have_aw <= 1'b0;
          have_w <= 1'b0;
        end
      end
    end
  end
endmodule
