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

 logic [31:0] aw_addr [0:2];
 logic aw_val [0:2];
 logic [1:0] aw_rd, aw_wr, aw_cnt;
 logic [31:0] w_data [0:2];
 logic [3:0]  w_strb [0:2];
 logic w_val [0:2];
 logic [1:0] w_rd, w_wr, w_cnt;
 logic [31:0] ar_addr [0:2];
 logic ar_val [0:2];
 logic [1:0] ar_rd, ar_wr, ar_cnt;

 logic [1:0] b_resp [0:2];
 logic b_val [0:2];
 logic [1:0] b_rd, b_wr, b_cnt;
 logic [31:0] r_data [0:2];
 logic [1:0]  r_resp [0:2];
 logic r_val [0:2];
 logic [1:0] r_rd, r_wr, r_cnt;

 localparam logic [1:0] E_IDLE=2'd0, E_SETUP=2'd1, E_ACCESS=2'd2;
 logic [1:0] estate;
 logic pref;

 logic [31:0] ex_addr, ex_wdata;
 logic [3:0]  ex_strb;
 logic        ex_write;

 logic aw_full, w_full, ar_full;
 logic aw_avail, w_avail, ar_avail;

 assign aw_full = (aw_cnt == 2'd3);
 assign w_full  = (w_cnt  == 2'd3);
 assign ar_full = (ar_cnt == 2'd3);
 assign aw_avail = (aw_cnt != 0);
 assign w_avail  = (w_cnt  != 0);
 assign ar_avail = (ar_cnt != 0);

 assign s_awready = rst_n && !aw_full;
 assign s_wready  = rst_n && !w_full;
 assign s_arready = rst_n && !ar_full;

 assign s_bvalid = rst_n && (b_cnt != 0);
 assign s_bresp  = (b_cnt != 0) ? b_resp[b_rd] : 2'b00;

 assign s_rvalid = rst_n && (r_cnt != 0);
 assign s_rdata  = (r_cnt != 0) ? r_data[r_rd] : 32'b0;
 assign s_rresp  = (r_cnt != 0) ? r_resp[r_rd] : 2'b00;

 assign paddr  = ex_addr;
 assign pwdata = ex_wdata;
 assign pstrb  = ex_strb;
 assign pprot  = 3'b000;
 assign pwrite = ex_write;
 assign psel   = (estate != E_IDLE);
 assign penable= (estate == E_ACCESS);

 logic wr_elig, rd_elig;
 logic sel_write, sel_read, do_grant;
 assign wr_elig = aw_avail && w_avail;
 assign rd_elig = ar_avail;

 always_comb begin
   sel_write = 1'b0;
   sel_read  = 1'b0;
   do_grant  = 1'b0;
   if (estate == E_IDLE) begin
     if (wr_elig && rd_elig) begin
       if (pref) sel_read = 1'b1; else sel_write = 1'b1;
     end else if (wr_elig) sel_write = 1'b1;
     else if (rd_elig) sel_read = 1'b1;
     do_grant = sel_write || sel_read;
   end
 end

 wire aw_hs = s_awvalid && s_awready;
 wire w_hs  = s_wvalid  && s_wready;
 wire ar_hs = s_arvalid && s_arready;
 wire b_hs  = s_bvalid  && s_bready;
 wire r_hs  = s_rvalid  && s_rready;

 integer i;

 always_ff @(posedge clk) begin
   if (!rst_n) begin
     aw_rd <= 0; aw_wr <= 0; aw_cnt <= 0;
     w_rd  <= 0; w_wr  <= 0; w_cnt  <= 0;
     ar_rd <= 0; ar_wr <= 0; ar_cnt <= 0;
     b_rd  <= 0; b_wr  <= 0; b_cnt  <= 0;
     r_rd  <= 0; r_wr  <= 0; r_cnt  <= 0;
     for (i=0;i<3;i=i+1) begin
       aw_val[i] <= 1'b0; w_val[i] <= 1'b0; ar_val[i] <= 1'b0;
       b_val[i]  <= 1'b0; r_val[i] <= 1'b0;
     end
     estate <= E_IDLE;
     pref   <= 1'b1;
     ex_addr <= 0; ex_wdata <= 0; ex_strb <= 0; ex_write <= 0;
   end else begin
     case (estate)
       E_IDLE: begin
         if (do_grant) begin
           if (sel_write) begin
             ex_addr  <= aw_addr[aw_rd];
             ex_wdata <= w_data[w_rd];
             ex_strb  <= w_strb[w_rd];
             ex_write <= 1'b1;
             aw_val[aw_rd] <= 1'b0;
             w_val[w_rd]   <= 1'b0;
             aw_rd <= aw_rd + 2'd1;
             w_rd  <= w_rd  + 2'd1;
             aw_cnt <= aw_cnt - 2'd1;
             w_cnt  <= w_cnt  - 2'd1;
             pref <= 1'b0;
           end else begin
             ex_addr  <= ar_addr[ar_rd];
             ex_wdata <= 32'b0;
             ex_strb  <= 4'b0;
             ex_write <= 1'b0;
             ar_val[ar_rd] <= 1'b0;
             ar_rd <= ar_rd + 2'd1;
             ar_cnt <= ar_cnt - 2'd1;
             pref <= 1'b1;
           end
           estate <= E_SETUP;
         end
       end
       E_SETUP: begin
         estate <= E_ACCESS;
       end
       E_ACCESS: begin
         if (pready) begin
           if (ex_write) begin
             b_resp[b_wr] <= pslverr ? 2'b10 : 2'b00;
             b_val[b_wr]  <= 1'b1;
             b_wr  <= b_wr + 2'd1;
             b_cnt <= b_cnt + 2'd1;
           end else begin
             r_data[r_wr] <= prdata;
             r_resp[r_wr] <= pslverr ? 2'b10 : 2'b00;
             r_val[r_wr]  <= 1'b1;
             r_wr  <= r_wr + 2'd1;
             r_cnt <= r_cnt + 2'd1;
           end
           estate <= E_IDLE;
         end
       end
       default: estate <= E_IDLE;
     endcase

     if (aw_hs) begin
       aw_addr[aw_wr] <= s_awaddr;
       aw_val[aw_wr]  <= 1'b1;
       aw_wr  <= aw_wr + 2'd1;
       aw_cnt <= aw_cnt + 2'd1;
     end

     if (w_hs) begin
       w_data[w_wr] <= s_wdata;
       w_strb[w_wr] <= s_wstrb;
       w_val[w_wr]  <= 1'b1;
       w_wr  <= w_wr + 2'd1;
       w_cnt <= w_cnt + 2'd1;
     end

     if (ar_hs) begin
       ar_addr[ar_wr] <= s_araddr;
       ar_val[ar_wr]  <= 1'b1;
       ar_wr  <= ar_wr + 2'd1;
       ar_cnt <= ar_cnt + 2'd1;
     end

     if (b_hs) begin
       b_val[b_rd] <= 1'b0;
       b_rd  <= b_rd + 2'd1;
       b_cnt <= b_cnt - 2'd1;
     end

     if (r_hs) begin
       r_val[r_rd] <= 1'b0;
       r_rd  <= r_rd + 2'd1;
       r_cnt <= r_cnt - 2'd1;
     end
   end
 end

endmodule
