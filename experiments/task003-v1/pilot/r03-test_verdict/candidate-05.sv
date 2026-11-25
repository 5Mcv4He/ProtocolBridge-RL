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
 logic [1:0]  aw_n;
 logic [31:0] w_data [0:1];
 logic [3:0]  w_strb [0:1];
 logic [1:0]  w_n;
 logic [31:0] ar_addr [0:1];
 logic [1:0]  ar_n;

 logic        busy;
 logic        apb_setup;
 logic        rd_pend;
 logic        wr_pend;
 logic [31:0] resp_data;
 logic [1:0]  resp_code;
 logic [31:0] cur_addr;
 logic        cur_write;
 logic [31:0] cur_wdata;
 logic [3:0]  cur_strb;

 logic pref;

 wire aw_wr = s_awvalid && s_awready;
 wire w_wr  = s_wvalid  && s_wready;
 wire ar_wr = s_arvalid && s_arready;
 wire b_rd  = s_bvalid  && s_bready;
 wire r_rd  = s_rvalid  && s_rready;

 assign s_awready = (aw_n < 2'd2);
 assign s_wready  = (w_n  < 2'd2);
 assign s_arready = (ar_n < 2'd2);

 wire wr_elig = (aw_n != 0) && (w_n != 0);
 wire rd_elig = (ar_n != 0);
 wire idle = ~busy && ~rd_pend && ~wr_pend;
 wire any_elig = wr_elig || rd_elig;
 wire start = idle && any_elig;
 wire do_write_sel = start && wr_elig && (!rd_elig || pref);
 wire do_read_sel  = start && rd_elig && (!wr_elig || ~pref);

 always_comb begin
   psel    = busy;
   penable = busy && apb_setup;
   pwrite  = cur_write;
   paddr   = cur_addr;
   pwdata  = cur_wdata;
   pstrb   = cur_write ? cur_strb : 4'b0000;
   pprot   = 3'b000;
   s_bvalid = wr_pend;
   s_bresp  = resp_code;
   s_rvalid = rd_pend;
   s_rdata  = resp_data;
   s_rresp  = resp_code;
 end

 wire apb_done = busy && apb_setup && pready;

 always_ff @(posedge clk) begin
   if (!rst_n) begin
     aw_n <= 2'd0;
     w_n  <= 2'd0;
     ar_n <= 2'd0;
     busy <= 1'b0;
     apb_setup <= 1'b0;
     rd_pend <= 1'b0;
     wr_pend <= 1'b0;
     resp_data <= 32'b0;
     resp_code <= 2'b00;
     cur_addr <= 32'b0;
     cur_write <= 1'b0;
     cur_wdata <= 32'b0;
     cur_strb <= 4'b0;
     pref <= 1'b0;
   end else begin
     if (b_rd) begin
       if (aw_n == 2'd2) begin
         aw_addr[0] <= aw_addr[1];
         aw_n <= 2'd1;
       end else if (aw_n == 2'd1) begin
         aw_n <= 2'd0;
       end
     end
     if (aw_wr) begin
       if (b_rd && aw_n == 2'd2) begin
         aw_addr[1] <= s_awaddr;
         aw_n <= 2'd2;
       end else if (b_rd && aw_n == 2'd1) begin
         aw_addr[0] <= s_awaddr;
         aw_n <= 2'd1;
       end else if (aw_n == 2'd1) begin
         aw_addr[1] <= s_awaddr;
         aw_n <= 2'd2;
       end else if (aw_n == 2'd0) begin
         aw_addr[0] <= s_awaddr;
         aw_n <= 2'd1;
       end
     end

     if (b_rd) begin
       if (w_n == 2'd2) begin
         w_data[0] <= w_data[1];
         w_strb[0] <= w_strb[1];
         w_n <= 2'd1;
       end else if (w_n == 2'd1) begin
         w_n <= 2'd0;
       end
     end
     if (w_wr) begin
       if (b_rd && w_n == 2'd2) begin
         w_data[1] <= s_wdata;
         w_strb[1] <= s_wstrb;
         w_n <= 2'd2;
       end else if (b_rd && w_n == 2'd1) begin
         w_data[0] <= s_wdata;
         w_strb[0] <= s_wstrb;
         w_n <= 2'd1;
       end else if (w_n == 2'd1) begin
         w_data[1] <= s_wdata;
         w_strb[1] <= s_wstrb;
         w_n <= 2'd2;
       end else if (w_n == 2'd0) begin
         w_data[0] <= s_wdata;
         w_strb[0] <= s_wstrb;
         w_n <= 2'd1;
       end
     end

     if (r_rd) begin
       if (ar_n == 2'd2) begin
         ar_addr[0] <= ar_addr[1];
         ar_n <= 2'd1;
       end else if (ar_n == 2'd1) begin
         ar_n <= 2'd0;
       end
     end
     if (ar_wr) begin
       if (r_rd && ar_n == 2'd2) begin
         ar_addr[1] <= s_araddr;
         ar_n <= 2'd2;
       end else if (r_rd && ar_n == 2'd1) begin
         ar_addr[0] <= s_araddr;
         ar_n <= 2'd1;
       end else if (ar_n == 2'd1) begin
         ar_addr[1] <= s_araddr;
         ar_n <= 2'd2;
       end else if (ar_n == 2'd0) begin
         ar_addr[0] <= s_araddr;
         ar_n <= 2'd1;
       end
     end

     if (b_rd) wr_pend <= 1'b0;
     if (r_rd) rd_pend <= 1'b0;

     if (apb_done) begin
       resp_data <= cur_write ? 32'b0 : prdata;
       resp_code <= pslverr ? 2'b10 : 2'b00;
       busy <= 1'b0;
       apb_setup <= 1'b0;
       if (cur_write) wr_pend <= 1'b1;
       else rd_pend <= 1'b1;
     end else if (start) begin
       busy <= 1'b1;
       apb_setup <= 1'b0;
       if (do_write_sel) begin
         cur_addr <= aw_addr[0];
         cur_wdata <= w_data[0];
         cur_strb <= w_strb[0];
         cur_write <= 1'b1;
         pref <= 1'b0;
       end else begin
         cur_addr <= ar_addr[0];
         cur_wdata <= 32'b0;
         cur_strb <= 4'b0;
         cur_write <= 1'b0;
         pref <= 1'b1;
       end
     end else if (busy && !apb_setup) begin
       apb_setup <= 1'b1;
     end
   end
 end

endmodule
