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
 // States
 // 0: idle (accept requests)
 // 1: APB setup
 // 2: APB access
 // 3: response pending
 localparam [1:0] IDLE = 2'd0, SETUP = 2'd1, ACCESS = 2'd2, RESP = 2'd3;

 logic [1:0] state;

 // Captured write halves
 logic aw_have, w_have;
 logic [31:0] aw_addr_buf, w_data_buf;
 logic [3:0] w_strb_buf;

 // Current transaction info (latched at launch)
 logic cur_write; // 1 for write
 logic [31:0] req_addr;
 logic [31:0] req_wdata;
 logic [3:0] req_wstrb;

 // Response
 logic resp_write; // 1 if B response
 logic [1:0] resp_code;
 logic [31:0] resp_rdata;

 wire both_write = aw_have && w_have;
 wire can_launch = (state == IDLE) && (s_arvalid || both_write);
 // Read has priority when no complete write pending
 wire do_read = s_arvalid && !both_write;

 assign s_awready = (state == IDLE) && !aw_have && !do_read;
 assign s_wready  = (state == IDLE) && !w_have  && !do_read;
 assign s_arready = (state == IDLE) && !aw_have && !w_have;

 assign s_bvalid = (state == RESP) && resp_write;
 assign s_rvalid = (state == RESP) && !resp_write;
 assign s_bresp = resp_code;
 assign s_rresp = resp_code;
 assign s_rdata = resp_rdata;

 assign psel = (state == SETUP) || (state == ACCESS);
 assign penable = (state == ACCESS);
 assign pwrite = cur_write;
 assign paddr = req_addr;
 assign pwdata = req_wdata;
 assign pstrb = cur_write ? req_wstrb : 4'b0000;
 assign pprot = 3'b000;

 always_ff @(posedge clk) begin
  if (!rst_n) begin
   state <= IDLE;
   aw_have <= 1'b0;
   w_have <= 1'b0;
   aw_addr_buf <= 32'd0;
   w_data_buf <= 32'd0;
   w_strb_buf <= 4'd0;
   cur_write <= 1'b0;
   req_addr <= 32'd0;
   req_wdata <= 32'd0;
   req_wstrb <= 4'd0;
   resp_write <= 1'b0;
   resp_code <= 2'd0;
   resp_rdata <= 32'd0;
  end else begin
   case (state)
    IDLE: begin
     // Accept AR (launch immediately)
     if (s_arvalid && !both_write) begin
      cur_write <= 1'b0;
      req_addr <= s_araddr;
      req_wdata <= 32'd0;
      req_wstrb <= 4'd0;
      state <= SETUP;
     end else begin
      if (s_awvalid && !aw_have) begin
       aw_have <= 1'b1;
       aw_addr_buf <= s_awaddr;
      end
      if (s_wvalid && !w_have) begin
       w_have <= 1'b1;
       w_data_buf <= s_wdata;
       w_strb_buf <= s_wstrb;
      end
      // Launch write if both are present (either previously buffered or this cycle)
      if (both_write) begin
       cur_write <= 1'b1;
       req_addr <= aw_addr_buf;
       req_wdata <= w_data_buf;
       req_wstrb <= w_strb_buf;
       aw_have <= 1'b0;
       w_have <= 1'b0;
       state <= SETUP;
      end
     end
    end
    SETUP: begin
     state <= ACCESS;
    end
    ACCESS: begin
     if (pready) begin
      resp_write <= cur_write;
      resp_code <= pslverr ? 2'b10 : 2'b00;
      resp_rdata <= prdata;
      state <= RESP;
     end
    end
    RESP: begin
     if (resp_write && s_bready) begin
      state <= IDLE;
     end else if (!resp_write && s_rready) begin
      state <= IDLE;
     end
    end
   endcase
  end
 end
endmodule
