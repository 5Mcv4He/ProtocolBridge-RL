module bridge(
 input logic clk,rst_n,
 input logic [31:0] s_awaddr, input logic s_awvalid, output logic s_awready,
 input logic [31:0] s_wdata, input logic [3:0] s_wstrb, input logic s_wvalid, output logic s_wready,
 output logic [1:0] s_bresp, output logic s_bvalid, input logic s_bready,
 input logic [31:0] s_araddr, input logic s_arvalid, output logic s_arready,
 output logic [31:0] s_rdata, output logic [1:0] s_rresp, output logic s_rvalid, input logic s_rready,
 output logic [31:0] paddr,pwdata, output logic [3:0] pstrb, output logic [2:0] pprot,
 output logic [2:0] psel, input logic [95:0] prdata, input logic [2:0] pready,pslverr, output logic penable,pwrite
);

 // AW queue (depth 2)
 logic [31:0] aw_addr_q [0:1];
 logic aw_v_q [0:1];
 logic [1:0] aw_head, aw_tail;
 logic [1:0] aw_cnt;

 // W queue (depth 2)
 logic [31:0] w_data_q [0:1];
 logic [3:0]  w_strb_q [0:1];
 logic w_v_q [0:1];
 logic [1:0] w_head, w_tail;
 logic [1:0] w_cnt;

 // AR queue (depth 2)
 logic [31:0] ar_addr_q [0:1];
 logic ar_v_q [0:1];
 logic [1:0] ar_head, ar_tail;
 logic [1:0] ar_cnt;

 // Executor state
 // state: 0=IDLE, 1=SETUP, 2=ACCESS, 3=RESP
 logic [1:0] state;
 logic sel_is_write;
 logic [31:0] ex_addr;
 logic [31:0] ex_wdata;
 logic [3:0]  ex_wstrb;
 logic [1:0]  ex_target;
 logic ex_mapped;
 logic [31:0] ex_local_addr;

 // response regs
 logic s_bvalid_r, s_rvalid_r;
 logic [1:0] s_bresp_r, s_rresp_r;
 logic [31:0] s_rdata_r;

 // round robin preference: 1 = READ
 logic rr_read;

 // interior regs for APB outputs
 logic [2:0] psel_r;
 logic penable_r;
 logic pwrite_r;
 logic [31:0] paddr_r, pwdata_r;
 logic [3:0] pstrb_r;

 // combinational helpers
 logic [1:0] tgt_comb;
 logic mapped_comb;
 logic [31:0] local_comb;
 logic aw_have, w_have, ar_have;
 logic sel_valid;
 logic sel_w;
 logic [31:0] sel_addr;

 always_comb begin
   tgt_comb = 2'd0;
   mapped_comb = 1'b0;
   local_comb = 32'd0;
   // decode based on priority; only used after address chosen
 end

 // port outputs
 assign psel = psel_r;
 assign penable = penable_r;
 assign pwrite = pwrite_r;
 assign paddr = paddr_r;
 assign pwdata = pwdata_r;
 assign pstrb = pstrb_r;
 assign pprot = 3'b000;

 assign s_awready = (aw_cnt < 2'd2);
 assign s_wready  = (w_cnt  < 2'd2);
 assign s_arready = (ar_cnt < 2'd2);

 assign s_bvalid = s_bvalid_r;
 assign s_bresp  = s_bresp_r;
 assign s_rvalid = s_rvalid_r;
 assign s_rresp  = s_rresp_r;
 assign s_rdata  = s_rdata_r;

 // decode function
 function automatic void decode(input logic [31:0] a, output logic [1:0] t, output logic m, output logic [31:0] l);
   if (a[31:16] == 16'h0000) begin t = 2'd0; m = 1'b1; l = a - 32'h0000_0000; end
   else if (a[31:16] == 16'h0001) begin t = 2'd1; m = 1'b1; l = a - 32'h0001_0000; end
   else if (a[31:16] == 16'h0002) begin t = 2'd2; m = 1'b1; l = a - 32'h0002_0000; end
   else begin t = 2'd0; m = 1'b0; l = 32'd0; end
 endfunction

 logic [1:0]  dec_t;
 logic        dec_m;
 logic [31:0] dec_l;

 // selection combinational
 always_comb begin
   aw_have = (aw_cnt != 0);
   w_have  = (w_cnt != 0);
   ar_have = (ar_cnt != 0);
   sel_valid = 1'b0;
   sel_w = 1'b0;
   sel_addr = 32'd0;
   dec_t = 2'd0; dec_m = 1'b0; dec_l = 32'd0;
   if (aw_have && w_have && ar_have) begin
     if (rr_read) begin sel_valid = 1'b1; sel_w = 1'b0; sel_addr = ar_addr_q[ar_head]; end
     else begin sel_valid = 1'b1; sel_w = 1'b1; sel_addr = aw_addr_q[aw_head]; end
   end else if (aw_have && w_have) begin
     sel_valid = 1'b1; sel_w = 1'b1; sel_addr = aw_addr_q[aw_head];
   end else if (ar_have) begin
     sel_valid = 1'b1; sel_w = 1'b0; sel_addr = ar_addr_q[ar_head];
   end
   decode(sel_addr, dec_t, dec_m, dec_l);
 end

 integer i;

 always_ff @(posedge clk) begin
   if (!rst_n) begin
     aw_cnt <= 0; aw_head <= 0; aw_tail <= 0;
     w_cnt <= 0; w_head <= 0; w_tail <= 0;
     ar_cnt <= 0; ar_head <= 0; ar_tail <= 0;
     for (i = 0; i < 2; i = i + 1) begin
       aw_v_q[i] <= 1'b0; w_v_q[i] <= 1'b0; ar_v_q[i] <= 1'b0;
     end
     state <= 2'd0;
     sel_is_write <= 1'b0;
     ex_addr <= 0; ex_wdata <= 0; ex_wstrb <= 0;
     ex_target <= 0; ex_mapped <= 0; ex_local_addr <= 0;
     s_bvalid_r <= 1'b0; s_rvalid_r <= 1'b0;
     s_bresp_r <= 2'b00; s_rresp_r <= 2'b00; s_rdata_r <= 0;
     rr_read <= 1'b1;
     psel_r <= 0; penable_r <= 0; pwrite_r <= 0;
     paddr_r <= 0; pwdata_r <= 0; pstrb_r <= 0;
   end else begin
     // Reset default response handshakes
     if (s_bvalid_r && s_bready) s_bvalid_r <= 1'b0;
     if (s_rvalid_r && s_rready) s_rvalid_r <= 1'b0;

     // acceptance
     if (s_awready && s_awvalid) begin
       aw_addr_q[aw_tail] <= s_awaddr;
       aw_v_q[aw_tail] <= 1'b1;
       aw_tail <= aw_tail + 2'd1;
       aw_cnt <= aw_cnt + 2'd1;
     end
     if (s_wready && s_wvalid) begin
       w_data_q[w_tail] <= s_wdata;
       w_strb_q[w_tail] <= s_wstrb;
       w_v_q[w_tail] <= 1'b1;
       w_tail <= w_tail + 2'd1;
       w_cnt <= w_cnt + 2'd1;
     end
     if (s_arready && s_arvalid) begin
       ar_addr_q[ar_tail] <= s_araddr;
       ar_v_q[ar_tail] <= 1'b1;
       ar_tail <= ar_tail + 2'd1;
       ar_cnt <= ar_cnt + 2'd1;
     end

     // executor
     case (state)
       2'd0: begin
         // idle: select based on pre-edge queues
         psel_r <= 3'b000; penable_r <= 1'b0;
         if (sel_valid) begin
           // pop the selected queue head
           if (sel_w) begin
             if (aw_v_q[aw_head]) begin
               aw_v_q[aw_head] <= 1'b0;
               aw_head <= aw_head + 2'd1;
               aw_cnt <= aw_cnt - 2'd1;
             end
             if (w_v_q[w_head]) begin
               w_v_q[w_head] <= 1'b0;
               w_head <= w_head + 2'd1;
               w_cnt <= w_cnt - 2'd1;
             end
             ex_addr <= sel_addr;
             ex_wdata <= w_data_q[w_head];
             ex_wstrb <= w_strb_q[w_head];
             sel_is_write <= 1'b1;
           end else begin
             if (ar_v_q[ar_head]) begin
               ar_v_q[ar_head] <= 1'b0;
               ar_head <= ar_head + 2'd1;
               ar_cnt <= ar_cnt - 2'd1;
             end
             ex_addr <= sel_addr;
             sel_is_write <= 1'b0;
           end
           ex_target <= dec_t;
           ex_mapped <= dec_m;
           ex_local_addr <= dec_l;
           rr_read <= !sel_w;
           // go to setup or immediate DECERR response
           if (!dec_m) begin
             state <= 2'd3;
             if (sel_w) begin s_bresp_r <= 2'b11; s_bvalid_r <= 1'b1; end
             else begin s_rresp_r <= 2'b11; s_rdata_r <= 32'd0; s_rvalid_r <= 1'b1; end
           end else begin
             state <= 2'd1;
           end
         end
       end
       2'd1: begin
         // Setup cycle: drive PSEL with PENABLE=0
         psel_r <= (3'b001 << ex_target);
         penable_r <= 1'b0;
         pwrite_r <= sel_is_write;
         paddr_r <= ex_local_addr;
         pwdata_r <= ex_wdata;
         pstrb_r <= sel_is_write ? ex_wstrb : 4'b0000;
         state <= 2'd2;
       end
       2'd2: begin
         // Access: PENABLE=1 until PREADY of selected target
         penable_r <= 1'b1;
         if (pready[ex_target]) begin
           psel_r <= 3'b000;
           penable_r <= 1'b0;
           if (sel_is_write) begin
             s_bvalid_r <= 1'b1;
             s_bresp_r <= pslverr[ex_target] ? 2'b10 : 2'b00;
           end else begin
             s_rvalid_r <= 1'b1;
             s_rresp_r <= pslverr[ex_target] ? 2'b10 : 2'b00;
             case (ex_target)
               2'd0: s_rdata_r <= prdata[31:0];
               2'd1: s_rdata_r <= prdata[63:32];
               2'd2: s_rdata_r <= prdata[95:64];
               default: s_rdata_r <= 32'd0;
             endcase
           end
           state <= 2'd3;
         end
       end
       2'd3: begin
         // response pending: wait for consumption
         psel_r <= 3'b000; penable_r <= 1'b0;
         if ((s_bvalid_r && s_bready) || (s_rvalid_r && s_rready)) begin
           state <= 2'd0;
         end
       end
       default: state <= 2'd0;
     endcase
   end
 end

endmodule
