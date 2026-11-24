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

 logic aw_full; logic [31:0] aw_addr;
 logic w_full;  logic [31:0] w_data; logic [3:0] w_strb;

 logic [1:0] st; // 0 idle,1 setup,2 access
 logic t_wr; logic [31:0] t_addr,t_wdata; logic [3:0] t_strb;

 logic bv; logic [1:0] br;
 logic rv; logic [31:0] rd; logic [1:0] rr;

 logic busy;
 logic ar_acc;

 always_comb begin
   ar_acc=1'b0;
   s_awready=1'b0;
   s_wready=1'b0;
   if(!busy) begin
     if(!aw_full) s_awready=1'b1;
     if(!w_full)  s_wready=1'b1;
     if(!aw_full && !w_full && !w_valid_pending()) ar_acc=1'b1;
   end
 end

 function automatic logic w_valid_pending();
   return 1'b0;
 endfunction

 assign s_arready=ar_acc;
 assign s_bvalid=bv; assign s_bresp=br;
 assign s_rvalid=rv; assign s_rdata=rd; assign s_rresp=rr;
 assign paddr=t_addr; assign pwrite=t_wr;
 assign psel=(st!=2'd0); assign penable=(st==2'd2);
 assign pwdata=t_wdata;
 assign pstrb=t_wr?t_strb:4'b0000;
 assign pprot=3'b000;

 always_ff @(posedge clk) begin
   if(!rst_n) begin
     aw_full<=1'b0; aw_addr<=32'h0;
     w_full<=1'b0; w_data<=32'h0; w_strb<=4'h0;
     st<=2'd0; t_wr<=1'b0; t_addr<=32'h0; t_wdata<=32'h0; t_strb<=4'h0;
     bv<=1'b0; br<=2'b00; rv<=1'b0; rd<=32'h0; rr<=2'b00;
     busy<=1'b0;
   end else begin
     // response clears
     if(bv && s_bready) bv<=1'b0;
     if(rv && s_rready) rv<=1'b0;

     // recompute busy for this cycle from next states is tricky; handle separately
     // accept AR
     if(s_arvalid && ar_acc) begin
       t_wr<=1'b0; t_addr<=s_araddr; t_wdata<=32'h0; t_strb<=4'h0;
       st<=2'd1; busy<=1'b1;
     end
     // accept AW
     if(s_awvalid && s_awready) begin
       aw_full<=1'b1; aw_addr<=s_awaddr;
     end
     // accept W
     if(s_wvalid && s_wready) begin
       w_full<=1'b1; w_data<=s_wdata; w_strb<=s_wstrb;
     end

     case(st)
       2'd0: begin
         if(aw_full && w_full) begin
           t_wr<=1'b1; t_addr<=aw_addr; t_wdata<=w_data; t_strb<=w_strb;
           st<=2'd1; busy<=1'b1;
           aw_full<=1'b0; w_full<=1'b0;
         end
       end
       2'd1: begin
         st<=2'd2;
       end
       2'd2: begin
         if(pready) begin
           st<=2'd0;
           if(t_wr) begin
             bv<=1'b1; br<=pslverr?2'b10:2'b00;
           end else begin
             rv<=1'b1; rd<=prdata; rr<=pslverr?2'b10:2'b00;
           end
         end
       end
     endcase

     // busy release
     if(st==2'd0) begin
       if(bv && s_bready && !s_arvalid) busy<=1'b0;
       else if(rv && s_rready && !s_arvalid) busy<=1'b0;
       else if(!bv && !rv && !(aw_full&&w_full)) busy<=1'b0;
     end
   end
 end

endmodule