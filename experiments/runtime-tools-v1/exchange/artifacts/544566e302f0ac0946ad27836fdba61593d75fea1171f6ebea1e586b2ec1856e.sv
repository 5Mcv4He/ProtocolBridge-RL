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

 logic [31:0] aw_addr [0:1];
 logic [1:0]  aw_cnt;
 logic [31:0] w_data [0:1];
 logic [3:0]  w_strb [0:1];
 logic [1:0]  w_cnt;
 logic [31:0] ar_addr [0:1];
 logic [1:0]  ar_cnt;

 logic        b_pend;
 logic [1:0]  b_resp_r;
 logic        r_pend;
 logic [31:0] r_data_r;
 logic [1:0]  r_resp_r;

 logic [1:0]  apb_st;
 logic        cur_is_write;
 logic [31:0] cur_addr;
 logic [31:0] cur_wdata;
 logic [3:0]  cur_wstrb;

 logic        pref;

 logic aw_push, w_push, ar_push;
 logic write_elig, read_elig, start, sel_write, exec_free;
 logic b_pop, r_pop;

 assign b_pop = b_pend && s_bready;
 assign r_pop = r_pend && s_rready;

 always_comb begin
   s_awready = (aw_cnt < 2'd2);
   s_wready  = (w_cnt  < 2'd2);
   s_arready = (ar_cnt < 2'd2);
   aw_push = s_awvalid && s_awready;
   w_push  = s_wvalid  && s_wready;
   ar_push = s_arvalid && s_arready;
 end

 always_comb begin
   write_elig = (aw_cnt != 0) && (w_cnt != 0);
   read_elig  = (ar_cnt != 0);
   exec_free  = (apb_st == 2'd0);
 end

 always_comb begin
   start = 1'b0;
   sel_write = 1'b0;
   if (exec_free && (write_elig || read_elig)) begin
     start = 1'b1;
     if (write_elig && read_elig) sel_write = pref;
     else sel_write = write_elig;
   end
 end

 always_comb begin
   psel    = (apb_st != 2'd0);
   penable = (apb_st == 2'd2);
   pwrite  = cur_is_write;
   paddr   = cur_addr;
   pwdata  = cur_is_write ? cur_wdata : 32'd0;
   pstrb   = cur_is_write ? cur_wstrb : 4'd0;
   pprot   = 3'b000;
   s_bvalid = b_pend;
   s_bresp  = b_resp_r;
   s_rvalid = r_pend;
   s_rdata  = r_data_r;
   s_rresp  = r_resp_r;
 end

 integer i;
 always_ff @(posedge clk) begin
   if (!rst_n) begin
     aw_cnt <= 2'd0;
     w_cnt  <= 2'd0;
     ar_cnt <= 2'd0;
     for (i=0;i<2;i=i+1) begin
       aw_addr[i] <= 32'd0;
       w_data[i]  <= 32'd0;
       w_strb[i]  <= 4'd0;
       ar_addr[i] <= 32'd0;
     end
     b_pend <= 1'b0;
     b_resp_r <= 2'd0;
     r_pend <= 1'b0;
     r_data_r <= 32'd0;
     r_resp_r <= 2'd0;
     apb_st <= 2'd0;
     cur_is_write <= 1'b0;
     cur_addr <= 32'd0;
     cur_wdata <= 32'd0;
     cur_wstrb <= 4'd0;
     pref <= 1'b0;
   end else begin
     case (apb_st)
       2'd1: apb_st <= 2'd2;
       2'd2: begin
         if (pready) begin
           apb_st <= 2'd0;
           if (cur_is_write) begin
             b_pend   <= 1'b1;
             b_resp_r <= pslverr ? 2'b10 : 2'b00;
           end else begin
             r_pend   <= 1'b1;
             r_data_r <= prdata;
             r_resp_r <= pslverr ? 2'b10 : 2'b00;
           end
         end
       end
       default: begin
         if (start) begin
           apb_st <= 2'd1;
           cur_is_write <= sel_write;
           pref <= ~sel_write;
           if (sel_write) begin
             cur_addr  <= aw_addr[0];
             cur_wdata <= w_data[0];
             cur_wstrb <= w_strb[0];
           end else begin
             cur_addr  <= ar_addr[0];
           end
         end
       end
     endcase

     if (b_pop) b_pend <= 1'b0;
     if (r_pop) r_pend <= 1'b0;

     // ---- AW queue ----
     if (start && sel_write) begin
       aw_addr[0] <= aw_addr[1];
       if (aw_push) aw_addr[1] <= s_awaddr;
       aw_cnt <= aw_cnt; // pop one, push one
       if (!aw_push) aw_cnt <= aw_cnt - 2'd1;
     end else if (aw_push) begin
       aw_addr[aw_cnt] <= s_awaddr;
       aw_cnt <= aw_cnt + 2'd1;
     end

     // ---- W queue ----
     if (start && sel_write) begin
       w_data[0] <= w_data[1];
       w_strb[0] <= w_strb[1];
       if (w_push) begin
         w_data[1] <= s_wdata;
         w_strb[1] <= s_wstrb;
       end
       w_cnt <= w_cnt;
       if (!w_push) w_cnt <= w_cnt - 2'd1;
     end else if (w_push) begin
       w_data[w_cnt] <= s_wdata;
       w_strb[w_cnt] <= s_wstrb;
       w_cnt <= w_cnt + 2'd1;
     end

     // ---- AR queue ----
     if (start && !sel_write) begin
       ar_addr[0] <= ar_addr[1];
       if (ar_push) ar_addr[1] <= s_araddr;
       ar_cnt <= ar_cnt;
       if (!ar_push) ar_cnt <= ar_cnt - 2'd1;
     end else if (ar_push) begin
       ar_addr[ar_cnt] <= s_araddr;
       ar_cnt <= ar_cnt + 2'd1;
     end
   end
 end
endmodule