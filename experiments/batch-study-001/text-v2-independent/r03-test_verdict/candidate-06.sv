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

 localparam logic [1:0]
   IDLE      = 2'd0,
   APB_SETUP = 2'd1,
   APB_ACCESS= 2'd2,
   RESP      = 2'd3;

 logic [1:0] state;

 logic aw_have;
 logic [31:0] aw_addr;
 logic w_have;
 logic [31:0] w_data;
 logic [3:0]  w_strb;

 logic ar_have;
 logic [31:0] ar_addr;

 logic resp_is_write;
 logic [31:0] resp_rdata;
 logic [1:0]  resp_resp;

 logic [31:0] apb_addr;
 logic        apb_write;
 logic [31:0] apb_wdata;
 logic [3:0]  apb_strb;

 logic bus_free;
 assign bus_free = (state==IDLE) && !s_bvalid && !s_rvalid;

 assign s_awready = rst_n && bus_free && !aw_have && !ar_have && !w_have;
 assign s_wready  = rst_n && bus_free && !w_have && !ar_have;
 assign s_arready = rst_n && bus_free && !ar_have && !aw_have && !w_have;

 assign pprot = 3'b000;

 // combinational launch decision
 logic        do_read;
 logic        do_write;
 logic [31:0] launch_addr;
 logic [31:0] launch_wdata;
 logic [3:0]  launch_strb;

 always_comb begin
   do_read  = 1'b0;
   do_write = 1'b0;
   launch_addr = 32'b0;
   launch_wdata = 32'b0;
   launch_strb = 4'b0;
   if (state==IDLE && !s_bvalid && !s_rvalid) begin
     if (ar_have || (s_arvalid && s_arready)) begin
       do_read = 1'b1;
       launch_addr = ar_have ? ar_addr : s_araddr;
     end else begin
       logic ah, wh;
       logic [31:0] aaddr, wd;
       logic [3:0] ws;
       ah = aw_have || (s_awvalid && s_awready);
       wh = w_have  || (s_wvalid && s_wready);
       aaddr = aw_have ? aw_addr : s_awaddr;
       wd = w_have ? w_data : s_wdata;
       ws = w_have ? w_strb : s_wstrb;
       if (ah && wh) begin
         do_write = 1'b1;
         launch_addr = aaddr;
         launch_wdata = wd;
         launch_strb = ws;
       end
     end
   end
 end

 always_ff @(posedge clk) begin
   if (!rst_n) begin
     state         <= IDLE;
     aw_have       <= 1'b0;
     aw_addr       <= 32'b0;
     w_have        <= 1'b0;
     w_data        <= 32'b0;
     w_strb        <= 4'b0;
     ar_have       <= 1'b0;
     ar_addr       <= 32'b0;
     resp_is_write <= 1'b0;
     resp_rdata    <= 32'b0;
     resp_resp     <= 2'b00;
     apb_addr      <= 32'b0;
     apb_write     <= 1'b0;
     apb_wdata     <= 32'b0;
     apb_strb      <= 4'b0;
     psel          <= 1'b0;
     penable       <= 1'b0;
     pwrite        <= 1'b0;
     paddr         <= 32'b0;
     pwdata        <= 32'b0;
     pstrb         <= 4'b0;
     s_bresp       <= 2'b00;
     s_bvalid      <= 1'b0;
     s_rdata       <= 32'b0;
     s_rresp       <= 2'b00;
     s_rvalid      <= 1'b0;
   end else begin
     psel    <= 1'b0;
     penable <= 1'b0;

     case (state)
       IDLE: begin
         if (s_awvalid && s_awready) begin
           aw_have <= 1'b1;
           aw_addr <= s_awaddr;
         end
         if (s_wvalid && s_wready) begin
           w_have <= 1'b1;
           w_data <= s_wdata;
           w_strb <= s_wstrb;
         end
         if (s_arvalid && s_arready) begin
           ar_have <= 1'b1;
           ar_addr <= s_araddr;
         end

         if (do_read) begin
           apb_addr      <= launch_addr;
           apb_write     <= 1'b0;
           apb_wdata     <= 32'b0;
           apb_strb      <= 4'b0;
           resp_is_write <= 1'b0;
           ar_have       <= 1'b0;
           aw_have       <= 1'b0;
           w_have        <= 1'b0;
           state         <= APB_SETUP;
           psel          <= 1'b1;
           penable       <= 1'b0;
           pwrite        <= 1'b0;
           paddr         <= launch_addr;
           pwdata        <= 32'b0;
           pstrb         <= 4'b0;
         end else if (do_write) begin
           apb_addr      <= launch_addr;
           apb_write     <= 1'b1;
           apb_wdata     <= launch_wdata;
           apb_strb      <= launch_strb;
           resp_is_write <= 1'b1;
           aw_have       <= 1'b0;
           w_have        <= 1'b0;
           ar_have       <= 1'b0;
           state         <= APB_SETUP;
           psel          <= 1'b1;
           penable       <= 1'b0;
           pwrite        <= 1'b1;
           paddr         <= launch_addr;
           pwdata        <= launch_wdata;
           pstrb         <= launch_strb;
         end
       end

       APB_SETUP: begin
         psel    <= 1'b1;
         penable <= 1'b1;
         paddr   <= apb_addr;
         pwrite  <= apb_write;
         pwdata  <= apb_write ? apb_wdata : 32'b0;
         pstrb   <= apb_write ? apb_strb  : 4'b0;
         state   <= APB_ACCESS;
       end

       APB_ACCESS: begin
         psel    <= 1'b1;
         penable <= 1'b1;
         paddr   <= apb_addr;
         pwrite  <= apb_write;
         pwdata  <= apb_write ? apb_wdata : 32'b0;
         pstrb   <= apb_write ? apb_strb  : 4'b0;
         if (pready) begin
           if (apb_write) begin
             s_bvalid <= 1'b1;
             s_bresp  <= pslverr ? 2'b10 : 2'b00;
           end else begin
             s_rvalid <= 1'b1;
             s_rdata  <= prdata;
             s_rresp  <= pslverr ? 2'b10 : 2'b00;
           end
           resp_is_write <= apb_write;
           resp_rdata    <= prdata;
           resp_resp     <= pslverr ? 2'b10 : 2'b00;
           psel          <= 1'b0;
           penable       <= 1'b0;
           state         <= RESP;
         end
       end

       RESP: begin
         psel    <= 1'b0;
         penable <= 1'b0;
         if (resp_is_write) begin
           if (s_bready) begin
             s_bvalid <= 1'b0;
             state    <= IDLE;
           end
         end else begin
           if (s_rready) begin
             s_rvalid <= 1'b0;
             state    <= IDLE;
           end
         end
       end

       default: state <= IDLE;
     endcase
   end
 end

endmodule
