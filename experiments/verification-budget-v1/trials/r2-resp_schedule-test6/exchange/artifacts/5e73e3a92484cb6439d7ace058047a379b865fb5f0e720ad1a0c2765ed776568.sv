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

 // When idle this cycle, selection is driven by the pre-edge buffered
 // requests. When in a response state, the retiring response consumes one
 // credit and the new head must also be visible for same-edge selection
 // (i.e., new requests selected on the SAME edge they become usable).
 logic retire_b, retire_r;
 logic [1:0] aw_eff, w_eff, ar_eff;
 logic idle_sel;

 assign retire_b = resp_valid && resp_write  && s_bready;
 assign retire_r = resp_valid && !resp_write && s_rready;

 assign s_awready = (!retire_b && aw_count < 2'd3) || (retire_b && aw_count < 2'd2);
 assign s_wready  = (!retire_b && w_count  < 2'd3) || (retire_b && w_count  < 2'd2);
 assign s_arready = (!retire_r && ar_count < 2'd3) || (retire_r && ar_count < 2'd2);

 // Effective counts for selection: pre-edge minus same-edge retirement.
 assign aw_eff = (retire_b && aw_count != 2'd0) ? aw_count - 2'd1 : aw_count;
 assign w_eff  = (retire_b && w_count  != 2'd0) ? w_count  - 2'd1 : w_count;
 assign ar_eff = (retire_r && ar_count != 2'd0) ? ar_count - 2'd1 : ar_count;

 assign s_bvalid = resp_valid && resp_write;
 assign s_bresp  = resp_err ? 2'b10 : 2'b00;
 assign s_rvalid = resp_valid && !resp_write;
 assign s_rdata  = resp_rdata;
 assign s_rresp  = resp_err ? 2'b10 : 2'b00;

 assign paddr  = (state == S_IDLE) ? 32'b0 : inf_addr;
 assign pwdata = (state == S_IDLE) ? 32'b0 : inf_wdata;
 assign pstrb  = (state == S_IDLE) ? 4'b0 : inf_wstrb;
 assign pwrite = (state == S_IDLE) ? 1'b0 : inf_write;
 assign pprot  = 3'b000;
 assign psel   = (state == S_SETUP) || (state == S_ACC);
 assign penable = (state == S_ACC);

 integer i;

 // Combinatorial selection view.
 logic sel_aw_ok;
 logic sel_w_ok;
 logic sel_read_ok;
 logic sel_write_ok;
 logic sel_active;
 logic sel_pick_write;

 assign sel_aw_ok    = (aw_eff != 2'd0);
 assign sel_w_ok     = (w_eff  != 2'd0);
 assign sel_write_ok = sel_aw_ok && sel_w_ok;
 assign sel_read_ok  = (ar_eff != 2'd0);
 assign sel_active   = (sel_write_ok || sel_read_ok);
 // pref: 0 = read, 1 = write
 assign sel_pick_write = sel_write_ok && ((!sel_read_ok) || pref);

 // Selection may happen this cycle when the executor is idle now, or when a
 // pending response is being consumed on this edge (making it idle next).
 assign idle_sel = (state == S_IDLE) ||
                   (state == S_RESP && resp_valid && ((resp_write && s_bready) ||
                                                      (!resp_write && s_rready)));

 // New head index after same-edge retirement.
 logic [1:0] aw_nhead, w_nhead, ar_nhead;
 assign aw_nhead = (aw_head == 2'd2) ? 2'd0 : (aw_head + 2'd1);
 assign w_nhead  = (w_head  == 2'd2) ? 2'd0 : (w_head  + 2'd1);
 assign ar_nhead = (ar_head == 2'd2) ? 2'd0 : (ar_head + 2'd1);

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
     end
     if (s_wvalid && s_wready) begin
       w_q[w_tail]  <= s_wdata;
       ws_q[w_tail] <= s_wstrb;
       w_tail <= (w_tail == 2'd2) ? 2'd0 : (w_tail + 2'd1);
     end
     if (s_arvalid && s_arready) begin
       ar_q[ar_tail] <= s_araddr;
       ar_tail <= (ar_tail == 2'd2) ? 2'd0 : (ar_tail + 2'd1);
     end

     // response consumption retires credits
     if (retire_b) begin
       resp_valid <= 1'b0;
       aw_head <= aw_nhead;
       w_head  <= w_nhead;
     end else if (retire_r) begin
       resp_valid <= 1'b0;
       ar_head <= ar_nhead;
     end

     // combined count update
     aw_count <= aw_eff + ((s_awvalid && s_awready) ? 2'd1 : 2'd0);
     w_count  <= w_eff  + ((s_wvalid  && s_wready)  ? 2'd1 : 2'd0);
     ar_count <= ar_eff + ((s_arvalid && s_arready) ? 2'd1 : 2'd0);

     case (state)
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
       default: ;
     endcase

     // Selection: driven by pre-edge (adjusted) buffered requests. Select on
     // the edge the executor becomes free so setup follows immediately.
     if (idle_sel && sel_active) begin
       if (sel_pick_write) begin
         inf_write <= 1'b1;
         inf_addr  <= aw_q[retire_b ? aw_nhead : aw_head];
         inf_wdata <= w_q[retire_b ? w_nhead : w_head];
         inf_wstrb <= ws_q[retire_b ? w_nhead : w_head];
         pref <= 1'b0;
       end else begin
         inf_write <= 1'b0;
         inf_addr  <= ar_q[retire_r ? ar_nhead : ar_head];
         inf_wdata <= 32'b0;
         inf_wstrb <= 4'b0;
         pref <= 1'b1;
       end
       state <= S_SETUP;
     end
   end
 end

endmodule
