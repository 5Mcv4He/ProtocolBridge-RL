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

  localparam [1:0] APB_IDLE = 2'd0, APB_SETUP = 2'd1, APB_ACCESS = 2'd2;

  logic [1:0] apb_state;

  logic        aw_have, w_have;
  logic [31:0] aw_addr_r;
  logic [31:0] w_data_r;
  logic [3:0]  w_strb_r;

  logic        cur_write;

  logic        bpend, rpend;
  logic [1:0]  bresp_r, rresp_r;
  logic [31:0] rdata_r;

  logic idle;
  assign idle = (apb_state == APB_IDLE) && !bpend && !rpend;

  assign s_awready = idle && !aw_have;
  assign s_wready  = idle && aw_have && !w_have;
  assign s_arready = idle && !aw_have && !w_have;

  assign s_bresp  = bresp_r;
  assign s_bvalid = bpend;
  assign s_rdata  = rdata_r;
  assign s_rresp  = rresp_r;
  assign s_rvalid = rpend;

  assign pprot    = 3'b000;
  assign psel     = (apb_state == APB_SETUP) || (apb_state == APB_ACCESS);
  assign penable  = (apb_state == APB_ACCESS);
  assign pwrite   = cur_write;
  assign paddr    = aw_addr_r;
  assign pwdata   = w_data_r;
  assign pstrb    = cur_write ? w_strb_r : 4'b0000;

  always_ff @(posedge clk) begin
    if (!rst_n) begin
      apb_state <= APB_IDLE;
      aw_have <= 1'b0;
      w_have  <= 1'b0;
      aw_addr_r <= 32'b0;
      w_data_r  <= 32'b0;
      w_strb_r  <= 4'b0;
      cur_write <= 1'b0;
      bpend <= 1'b0;
      rpend <= 1'b0;
      bresp_r <= 2'b00;
      rresp_r <= 2'b00;
      rdata_r <= 32'b0;
    end else begin
      if (bpend && s_bready) bpend <= 1'b0;
      if (rpend && s_rready) rpend <= 1'b0;

      if (s_awready && s_awvalid) begin
        aw_have <= 1'b1;
        aw_addr_r <= s_awaddr;
      end
      if (s_wready && s_wvalid) begin
        w_have <= 1'b1;
        w_data_r <= s_wdata;
        w_strb_r <= s_wstrb;
      end

      case (apb_state)
        APB_IDLE: begin
          if (aw_have && w_have) begin
            // both buffered - start write
            apb_state <= APB_SETUP;
            cur_write <= 1'b1;
            aw_have <= 1'b0;
            w_have  <= 1'b0;
          end else if (aw_have && (s_wready && s_wvalid)) begin
            // AW buffered, W arriving now
            apb_state <= APB_SETUP;
            cur_write <= 1'b1;
            aw_have <= 1'b0;
            w_have  <= 1'b0;
          end else if (s_arready && s_arvalid) begin
            cur_write <= 1'b0;
            aw_addr_r <= s_araddr;
            apb_state <= APB_SETUP;
          end
        end
        APB_SETUP: begin
          apb_state <= APB_ACCESS;
        end
        APB_ACCESS: begin
          if (pready) begin
            if (cur_write) begin
              bpend <= 1'b1;
              bresp_r <= pslverr ? 2'b10 : 2'b00;
            end else begin
              rpend <= 1'b1;
              rresp_r <= pslverr ? 2'b10 : 2'b00;
              rdata_r <= prdata;
            end
            apb_state <= APB_IDLE;
          end
        end
      endcase
    end
  end

endmodule