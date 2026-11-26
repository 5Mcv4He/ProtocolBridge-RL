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

 // apb_st: 0=idle, 1=setup, 2=access
 logic [1:0]  apb_st;
 logic        cur_is_write;
 logic [31:0] cur_addr;
 logic [31:0] cur_wdata;
 logic [3:0]  cur_wstrb;

 logic        pref;

 logic aw_push, w_push, ar_push;
 logic aw_pop, w_pop, ar_pop;
 logic write_elig, read_elig, start, sel_write, exec_free;

 // Pop occurs on the start edge (when a write/read is selected).
 // Push allowed when there is a free slot OR a same-edge pop frees one.
 always_comb begin
   start    = 1'b0;
   sel_write = 1'b0;
   write_elig = (aw_cnt != 0) && (w_cnt != 0);
   read_elig  = (ar_cnt != 0);
   exec_free  = (apb_st == 2'd0) && !b_pend && !r_pend;
   if (exec_free && (write_elig || read_elig)) begin
     start = 1'b1;
     if (write_elig && read_elig) sel_write = pref;
     else sel_write = write_elig;
   end
 end

 // Only pop the request actually selected this edge.
 always_comb begin
   aw_pop = start && sel_write;
   w_pop  = start && sel_write;
   ar_pop = start && !sel_write;
 end

 always_comb begin
   s_awready = (aw_cnt < 2'd2) || aw_pop;
   s_wready  = (w_cnt  < 2'd2) || w_pop;
   s_arready = (ar_cnt < 2'd2) || ar_pop;
   aw_push = s_awvalid && s_awready;
   w_push  = s_wvalid  && s_wready;
   ar_push = s_arvalid && s_arready;
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

     if (b_pend && s_bready) b_pend <= 1'b0;
     if (r_pend && s_rready) r_pend <= 1'b0;

     // ---- AW queue ----
     begin
       logic [1:0] ac;
       ac = aw_cnt;
       if (aw_pop) ac = ac - 2'd1;
       if (aw_pop) aw_addr[0] <= aw_addr[1];
       if (aw_push) aw_addr[ac] <= s_awaddr;
       if (aw_pop && aw_push)      aw_cnt <= aw_cnt;
       else if (aw_pop)            aw_cnt <= aw_cnt - 2'd1;
       else if (aw_push)           aw_cnt <= aw_cnt + 2'd1;
     end

     // ---- W queue ----
     begin
       logic [1:0] wc;
       wc = w_cnt;
       if (w_pop) wc = wc - 2'd1;
       if (w_pop) begin
         w_data[0] <= w_data[1];
         w_strb[0] <= w_strb[1];
       end
       if (w_push) begin
         w_data[wc] <= s_wdata;
         w_strb[wc] <= s_wstrb;
       end
       if (w_pop && w_push)        w_cnt <= w_cnt;
       else if (w_pop)             w_cnt <= w_cnt - 2'd1;
       else if (w_push)            w_cnt <= w_cnt + 2'd1;
     end

     // ---- AR queue ----
     begin
       logic [1:0] rc;
       rc = ar_cnt;
       if (ar_pop) rc = rc - 2'd1;
       if (ar_pop) ar_addr[0] <= ar_addr[1];
       if (ar_push) ar_addr[rc] <= s_araddr;
       if (ar_pop && ar_push)      ar_cnt <= ar_cnt;
       else if (ar_pop)            ar_cnt <= ar_cnt - 2'd1;
       else if (ar_push)           ar_cnt <= ar_cnt + 2'd1;
     end
   end
 end
endmodule