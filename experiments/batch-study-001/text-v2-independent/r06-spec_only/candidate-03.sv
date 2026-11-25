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

 // Buffered write halves
 logic        aw_full;
 logic [31:0] aw_addr;
 logic        w_full;
 logic [31:0] w_data;
 logic [3:0]  w_strb;

 // APB transaction state
 logic        apb_active;
 logic        apb_setup;
 logic        is_write;
 logic [31:0] req_addr;
 logic [31:0] req_wdata;
 logic [3:0]  req_strb;

 // Responses
 logic        bvalid_r;
 logic [1:0]  bresp_r;
 logic        rvalid_r;
 logic [31:0] rdata_r;
 logic [1:0]  rresp_r;

 // Can start a new transaction?
 logic idle;
 assign idle = (!apb_active) && (!bvalid_r) && (!rvalid_r);

 // Acceptance when idle only.
 assign s_awready = idle && !aw_full;
 assign s_wready  = idle && !w_full;
 assign s_arready = idle && !s_awvalid && !s_wvalid && !aw_full && !w_full;

 always_ff @(posedge clk) begin
   if (!rst_n) begin
     aw_full     <= 1'b0;
     aw_addr     <= 32'b0;
     w_full      <= 1'b0;
     w_data      <= 32'b0;
     w_strb      <= 4'b0;
     apb_active  <= 1'b0;
     apb_setup   <= 1'b0;
     is_write    <= 1'b0;
     req_addr    <= 32'b0;
     req_wdata   <= 32'b0;
     req_strb    <= 4'b0;
     bvalid_r    <= 1'b0;
     bresp_r     <= 2'b0;
     rvalid_r    <= 1'b0;
     rdata_r     <= 32'b0;
     rresp_r     <= 2'b0;
   end else begin
     // Response consumption
     if (bvalid_r && s_bready) bvalid_r <= 1'b0;
     if (rvalid_r && s_rready) rvalid_r <= 1'b0;

     // Request acceptance
     if (s_awready && s_awvalid) begin
       aw_full <= 1'b1;
       aw_addr <= s_awaddr;
     end
     if (s_wready && s_wvalid) begin
       w_full <= 1'b1;
       w_data <= s_wdata;
       w_strb <= s_wstrb;
     end

     // APB sequencing
     if (!apb_active) begin
       // Decide whether to start
       if (idle) begin
         if (!is_write && aw_full && w_full) begin
           // start write
           apb_active <= 1'b1;
           apb_setup  <= 1'b1;
           is_write   <= 1'b1;
           req_addr   <= aw_addr;
           req_wdata  <= w_data;
           req_strb   <= w_strb;
           aw_full    <= 1'b0;
           w_full     <= 1'b0;
         end else if (!aw_full && !w_full && !s_awvalid && !s_wvalid && s_arvalid) begin
           // start read
           apb_active <= 1'b1;
           apb_setup  <= 1'b1;
           is_write   <= 1'b0;
           req_addr   <= s_araddr;
           req_wdata  <= 32'b0;
           req_strb   <= 4'b0;
         end
       end
     end else begin
       if (apb_setup) begin
         apb_setup <= 1'b0;
       end else if (penable && pready) begin
         apb_active <= 1'b0;
         if (is_write) begin
           bvalid_r <= 1'b1;
           bresp_r  <= (pslverr ? 2'b10 : 2'b00);
         end else begin
           rvalid_r <= 1'b1;
           rdata_r  <= prdata;
           rresp_r  <= (pslverr ? 2'b10 : 2'b00);
         end
       end
     end
   end
 end

 assign psel   = apb_active;
 assign penable = apb_active && !apb_setup;
 assign pwrite = is_write;
 assign pprot  = 3'b000;
 assign paddr  = req_addr;
 assign pwdata = req_wdata;
 assign pstrb  = is_write ? req_strb : 4'b0;

 assign s_bvalid = bvalid_r;
 assign s_bresp  = bresp_r;
 assign s_rvalid = rvalid_r;
 assign s_rdata  = rdata_r;
 assign s_rresp  = rresp_r;

endmodule