// Read-only pin observation. Called before the existing checker samples an edge.
// No DUT internals, stimulus generation, expected payloads, or checker mutation.
int pb_cycle=0;
task pb_observe(input bit post_edge);
 if(pb_cycle<4096) begin
  $display("PBR1 %0d %0d %b %b %b %h %b %b %h %h %b %b %h %b %b %h %b %b %h %h %b %b %b %h %h %h %b %h %b",pb_cycle,post_edge,
   rst_n,s_awvalid,s_awready,s_awaddr,s_wvalid,s_wready,s_wdata,s_wstrb,
   s_arvalid,s_arready,s_araddr,s_bvalid,s_bready,s_bresp,s_rvalid,s_rready,s_rdata,s_rresp,
   psel,penable,pwrite,paddr,pwdata,pstrb,pready,prdata,pslverr);
 end
 if(pb_cycle==4096 && !post_edge) $display("PBR_LIMIT");
 if(post_edge) pb_cycle++;
endtask
