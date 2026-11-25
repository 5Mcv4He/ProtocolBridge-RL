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
 // TODO: implement the specified sequential bridge.

 // AW queue: 2 entries (circular, head/tail pointer + count)
 logic [31:0] aw_addr [0:1];
 logic aw_head, aw_tail;
 logic [1:0] aw_cnt;

 // W queue: 2 entries
 logic [31:0] w_data [0:1];
 logic [3:0]  w_strb [0:1];
 logic w_head, w_tail;
 logic [1:0] w_cnt;

 // AR queue: 2 entries
 logic [31:0] ar_addr [0:1];
 logic ar_head, ar_tail;
 logic [1:0] ar_cnt;

 // FSM states
 localparam IDLE=4'd0, SETUP=4'd1, ACCESS=4'd2, RESP=4'd3;
 logic [3:0] state;

 // preference: 0 = read, 1 = write
 logic pref;

 // active transaction info
 logic active_is_write;
 logic [31:0] act_addr;
 logic [31:0] act_wdata;
 logic [3:0]  act_strb;

 // pending response
 logic b_pend, r_pend;
 logic [1:0] b_resp_r, r_resp_r;
 logic [31:0] r_data_r;

 wire write_eligible = (aw_cnt!=0) && (w_cnt!=0);
 wire read_eligible  = (ar_cnt!=0);

 // acceptance ready: per-credit
 assign s_awready = (aw_cnt < 2);
 assign s_wready  = (w_cnt < 2);
 assign s_arready = (ar_cnt < 2);

 always_ff @(posedge clk) begin
   if(!rst_n) begin
     aw_head<=0; aw_tail<=0; aw_cnt<=0;
     w_head<=0; w_tail<=0; w_cnt<=0;
     ar_head<=0; ar_tail<=0; ar_cnt<=0;
     state<=IDLE; pref<=0;
     active_is_write<=0; act_addr<=0; act_wdata<=0; act_strb<=0;
     b_pend<=0; r_pend<=0; b_resp_r<=0; r_resp_r<=0; r_data_r<=0;
     s_bresp<=0; s_bvalid<=0;
     s_rdata<=0; s_rresp<=0; s_rvalid<=0;
     paddr<=0; pwdata<=0; pstrb<=0; pprot<=0;
     psel<=0; penable<=0; pwrite<=0;
   end else begin
     // default response outputs driven from pending state
     s_bvalid <= b_pend;
     s_bresp  <= b_resp_r;
     s_rvalid <= r_pend;
     s_rdata  <= r_data_r;
     s_rresp  <= r_resp_r;

     // default APB
     psel<=0; penable<=0;

     // ---- accept new requests (only when credit available) ----
     if(s_awvalid && s_awready) begin
       aw_addr[aw_tail] <= s_awaddr;
       aw_tail <= ~aw_tail;
       aw_cnt  <= aw_cnt + 1'b1;
     end
     if(s_wvalid && s_wready) begin
       w_data[w_tail] <= s_wdata;
       w_strb[w_tail] <= s_wstrb;
       w_tail <= ~w_tail;
       w_cnt  <= w_cnt + 1'b1;
     end
     if(s_arvalid && s_arready) begin
       ar_addr[ar_tail] <= s_araddr;
       ar_tail <= ~ar_tail;
       ar_cnt  <= ar_cnt + 1'b1;
     end

     // ---- response consumption ----
     if(b_pend && s_bready) begin
       b_pend <= 1'b0;
       aw_head <= ~aw_head;
       aw_cnt  <= aw_cnt - 1'b1;
       w_head  <= ~w_head;
       w_cnt   <= w_cnt  - 1'b1;
     end
     if(r_pend && s_rready) begin
       r_pend <= 1'b0;
       ar_head <= ~ar_head;
       ar_cnt  <= ar_cnt - 1'b1;
     end

     // ---- FSM ----
     case(state)
       IDLE: begin
         // determine eligibility based on queues BEFORE this edge
         if(read_eligible || write_eligible) begin
           // choose direction
           if(read_eligible && write_eligible) begin
             if(pref==0) begin
               // read
               active_is_write <= 0;
               act_addr <= ar_addr[ar_head];
               pref <= 1;
             end else begin
               active_is_write <= 1;
               act_addr <= aw_addr[aw_head];
               act_wdata <= w_data[w_head];
               act_strb <= w_strb[w_head];
               pref <= 0;
             end
           end else if(read_eligible) begin
             active_is_write <= 0;
             act_addr <= ar_addr[ar_head];
             pref <= 1;
           end else begin
             active_is_write <= 1;
             act_addr <= aw_addr[aw_head];
             act_wdata <= w_data[w_head];
             act_strb <= w_strb[w_head];
             pref <= 0;
           end
           state <= SETUP;
         end
       end
       SETUP: begin
         psel <= 1;
         penable <= 0;
         paddr <= act_addr;
         pwrite <= active_is_write;
         pwdata <= act_wdata;
         pstrb <= active_is_write ? act_strb : 4'b0;
         pprot <= 3'b000;
         state <= ACCESS;
       end
       ACCESS: begin
         psel <= 1;
         penable <= 1;
         paddr <= act_addr;
         pwrite <= active_is_write;
         pwdata <= act_wdata;
         pstrb <= active_is_write ? act_strb : 4'b0;
         pprot <= 3'b000;
         if(pready) begin
           if(active_is_write) begin
             b_pend <= 1'b1;
             b_resp_r <= pslverr ? 2'b10 : 2'b00;
           end else begin
             r_pend <= 1'b1;
             r_data_r <= prdata;
             r_resp_r <= pslverr ? 2'b10 : 2'b00;
           end
           state <= RESP;
         end
       end
       RESP: begin
         // wait for response consumed; executor holds until consumed
         // b_pend/r_pend clearing happens above; go idle after consumption
         if(active_is_write) begin
           if(b_pend && s_bready) state <= IDLE;
         end else begin
           if(r_pend && s_rready) state <= IDLE;
         end
       end
       default: state <= IDLE;
     endcase
   end
 end

endmodule
