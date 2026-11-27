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

 localparam S_IDLE  = 2'd0;
 localparam S_SETUP = 2'd1;
 localparam S_ACC   = 2'd2;
 localparam S_RESP  = 2'd3;

 logic [1:0] state;

 // AW queue
 logic [31:0] aw_q [0:2];
 logic [1:0]  aw_head;
 logic [1:0]  aw_count;
 logic [1:0]  aw_tail;

 // W queue
 logic [31:0] w_q [0:2];
 logic [3:0]  ws_q [0:2];
 logic [1:0]  w_head;
 logic [1:0]  w_count;
 logic [1:0]  w_tail;

 // AR queue
 logic [31:0] ar_q [0:2];
 logic [1:0]  ar_head;
 logic [1:0]  ar_count;
 logic [1:0]  ar_tail;

 // Round-robin preference: 0 = read, 1 = write
 logic pref;

 // In-flight APB transaction
 logic        inf_write;
 logic [31:0] inf_addr;
 logic [31:0] inf_wdata;
 logic [3:0]  inf_wstrb;

 // Pending AXI response
 logic        resp_valid;
 logic        resp_write;
 logic        resp_err;
 logic [31:0] resp_rdata;

 // Combinational "next" numbers to compute selection pre-edge
 wire [1:0] aw_count_n = aw_count;
 wire [1:0] w_count_n  = w_count;
 wire [1:0] ar_count_n = ar_count;

 assign s_awready = (aw_count < 2'd3);
 assign s_wready  = (w_count  < 2'd3);
 assign s_arready = (ar_count < 2'd3);

 assign s_bvalid = resp_valid && resp_write;
 assign s_bresp  = resp_err ? 2'b10 : 2'b00;
 assign s_rvalid = resp_valid && !resp_write;
 assign s_rdata  = resp_rdata;
 assign s_rresp  = resp_err ? 2'b10 : 2'b00;

 assign paddr  = (state == S_SETUP || state == S_ACC) ? inf_addr : 32'b0;
 assign pwdata = (state == S_SETUP || state == S_ACC) ? inf_wdata : 32'b0;
 assign pstrb  = (state == S_SETUP || state == S_ACC) ? inf_wstrb : 4'b0;
 assign pwrite = (state == S_SETUP || state == S_ACC) ? inf_write : 1'b0;
 assign pprot  = 3'b000;
 assign psel   = (state == S_SETUP) || (state == S_ACC);
 assign penable = (state == S_ACC);

 integer i;

 always_ff @(posedge clk) begin
   if (!rst_n) begin
     state <= S_IDLE;
     aw_head <= 2'd0; aw_count <= 2'd0; aw_tail <= 2'd0;
     w_head  <= 2'd0; w_count  <= 2'd0; w_tail  <= 2'd0;
     ar_head <= 2'd0; ar_count <= 2'd0; ar_tail <= 2'd0;
     pref <= 1'b0;
     inf_write <= 1'b0; inf_addr <= 32'b0; inf_wdata <= 32'b0; inf_wstrb <= 4'b0;
     resp_valid <= 1'b0; resp_write <= 1'b0; resp_err <= 1'b0; resp_rdata <= 32'b0;
     for (i = 0; i < 3; i = i + 1) begin
       aw_q[i] <= 32'b0;
       w_q[i]  <= 32'b0;
       ws_q[i] <= 4'b0;
       ar_q[i] <= 32'b0;
     end
   end else begin
     // accept new inputs
     if (s_awvalid && s_awready) begin
       aw_q[aw_tail] <= s_awaddr;
       aw_tail <= (aw_tail == 2'd2) ? 2'd0 : (aw_tail + 2'd1);
       aw_count <= aw_count + 2'd1;
     end
     if (s_wvalid && s_wready) begin
       w_q[w_tail]  <= s_wdata;
       ws_q[w_tail] <= s_wstrb;
       w_tail <= (w_tail == 2'd2) ? 2'd0 : (w_tail + 2'd1);
       w_count <= w_count + 2'd1;
     end
     if (s_arvalid && s_arready) begin
       ar_q[ar_tail] <= s_araddr;
       ar_tail <= (ar_tail == 2'd2) ? 2'd0 : (ar_tail + 2'd1);
       ar_count <= ar_count + 2'd1;
     end

     // response consumption retires credits
     if (resp_valid) begin
       if (resp_write && s_bready) begin
         resp_valid <= 1'b0;
         aw_head <= (aw_head == 2'd2) ? 2'd0 : (aw_head + 2'd1);
         aw_count <= aw_count - 2'd1;
         w_head  <= (w_head == 2'd2) ? 2'd0 : (w_head + 2'd1);
         w_count  <= w_count - 2'd1;
       end else if (!resp_write && s_rready) begin
         resp_valid <= 1'b0;
         ar_head <= (ar_head == 2'd2) ? 2'd0 : (ar_head + 2'd1);
         ar_count <= ar_count - 2'd1;
       end
     end

     case (state)
       S_IDLE: begin
       end
       S_SETUP: begin
         state <= S_ACC;
       end
       S_ACC: begin
         if (pready) begin
           resp_valid <= 1'b1;
           resp_write <= inf_write;
           resp_err   <= pslverr;
           resp_rdata <= prdata;
           state <= S_RESP;
         end
       end
       S_RESP: begin
         if (!resp_valid) state <= S_IDLE;
       end
       default: state <= S_IDLE;
     endcase

     // selection happens only when truly idle (no pending response).
     if (state == S_IDLE && !resp_valid) begin
       if (aw_count != 2'd0 && w_count != 2'd0 && ar_count != 2'd0) begin
         if (pref == 1'b1) begin
           inf_write <= 1'b1;
           inf_addr  <= aw_q[aw_head];
           inf_wdata <= w_q[w_head];
           inf_wstrb <= ws_q[w_head];
           pref <= 1'b0;
           state <= S_SETUP;
         end else begin
           inf_write <= 1'b0;
           inf_addr  <= ar_q[ar_head];
           inf_wdata <= 32'b0;
           inf_wstrb <= 4'b0;
           pref <= 1'b1;
           state <= S_SETUP;
         end
       end else if (aw_count != 2'd0 && w_count != 2'd0) begin
         inf_write <= 1'b1;
         inf_addr  <= aw_q[aw_head];
         inf_wdata <= w_q[w_head];
         inf_wstrb <= ws_q[w_head];
         pref <= 1'b0;
         state <= S_SETUP;
       end else if (ar_count != 2'd0) begin
         inf_write <= 1'b0;
         inf_addr  <= ar_q[ar_head];
         inf_wdata <= 32'b0;
         inf_wstrb <= 4'b0;
         pref <= 1'b1;
         state <= S_SETUP;
       end
     end
   end
 end

endmodule