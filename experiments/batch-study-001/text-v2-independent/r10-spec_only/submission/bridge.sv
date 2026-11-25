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
 logic aw_have, w_have, bpend, rpend;
 logic [31:0] awaddr_buf, wdata_buf;
 logic [3:0] wstrb_buf;
 logic [1:0] bresp_buf, rresp_buf;
 logic [31:0] rdata_buf;
 logic is_write, active, access;
 logic [31:0] aaddr, adata;
 logic [3:0] astrb;

 wire idle = !active && !bpend && !rpend;

 assign s_awready = idle && !aw_have && !w_have && !s_arvalid;
 assign s_wready  = idle && !w_have && !aw_have && !s_arvalid;
 assign s_arready = idle;

 assign pprot = 3'b000;
 assign psel = active;
 assign penable = active && access;

 always_comb begin
   if (active) begin
     paddr = aaddr; pwdata = adata; pstrb = astrb; pwrite = is_write;
   end else begin
     paddr = (aw_have || s_awvalid) ? (aw_have ? awaddr_buf : s_awaddr) : awaddr_buf;
     pwdata = w_have ? wdata_buf : s_wdata;
     pstrb = w_have ? wstrb_buf : s_wstrb;
     pwrite = 1'b1;
   end
 end

 always_ff @(posedge clk) begin
   if (!rst_n) begin
     aw_have <= 1'b0; w_have <= 1'b0;
     bpend <= 1'b0; rpend <= 1'b0;
     active <= 1'b0; access <= 1'b0; is_write <= 1'b0;
     awaddr_buf <= '0; wdata_buf <= '0; wstrb_buf <= '0;
     aaddr <= '0; adata <= '0; astrb <= '0;
     s_bvalid <= 1'b0; s_rvalid <= 1'b0;
     s_bresp <= 2'b00; s_rresp <= 2'b00; s_rdata <= '0;
     bresp_buf <= 2'b00; rresp_buf <= 2'b00; rdata_buf <= '0;
   end else begin
     // clear pending responses on handshake
     if (bpend && s_bready) bpend <= 1'b0;
     if (rpend && s_rready) rpend <= 1'b0;

     if (active) begin
       if (!access) begin
         access <= 1'b1;
       end else if (pready) begin
         active <= 1'b0; access <= 1'b0;
         if (is_write) begin
           bpend <= 1'b1;
           bresp_buf <= pslverr ? 2'b10 : 2'b00;
         end else begin
           rpend <= 1'b1;
           rdata_buf <= prdata;
           rresp_buf <= pslverr ? 2'b10 : 2'b00;
         end
       end
     end else begin
       // capture request halves
       if (s_awvalid && s_awready) begin
         awaddr_buf <= s_awaddr; aw_have <= 1'b1;
       end
       if (s_wvalid && s_wready) begin
         wdata_buf <= s_wdata; wstrb_buf <= s_wstrb; w_have <= 1'b1;
       end
       // launch
       if (idle) begin
         if ((aw_have || (s_awvalid && s_awready)) && (w_have || (s_wvalid && s_wready))) begin
           active <= 1'b1; access <= 1'b0; is_write <= 1'b1;
           aaddr <= aw_have ? awaddr_buf : s_awaddr;
           adata <= w_have ? wdata_buf : s_wdata;
           astrb <= w_have ? wstrb_buf : s_wstrb;
           aw_have <= 1'b0; w_have <= 1'b0;
         end else if (s_arvalid && s_arready) begin
           active <= 1'b1; access <= 1'b0; is_write <= 1'b0;
           aaddr <= s_araddr; adata <= '0; astrb <= '0;
         end
       end
     end

     s_bvalid <= bpend && !(s_bready && bpend) ? 1'b1 : (bpend && s_bready ? 1'b0 : bpend);
     s_bresp <= bresp_buf;
     s_rvalid <= rpend;
     s_rdata <= rdata_buf;
     s_rresp <= rresp_buf;
   end
 end
endmodule
