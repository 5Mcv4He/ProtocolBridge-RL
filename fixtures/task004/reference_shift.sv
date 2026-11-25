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
 // Three unretired credits per request channel. Execution consumes queued
 // requests; response consumption alone releases externally visible credits.
 localparam D=3;
 logic [31:0] aq[0:D-1],wq[0:D-1],rq[0:D-1],rdq[0:D-1];
 logic [3:0] sq[0:D-1];
 logic [1:0] bq[0:D-1],rrq[0:D-1];
 integer ac,wc,rc,an,wn,rn,bn,xn;
 logic pref;
 logic [1:0] state;
 wire ap=s_awvalid && s_awready,wp=s_wvalid && s_wready,rp=s_arvalid && s_arready;
 wire bp=s_bvalid && s_bready,xp=s_rvalid && s_rready;
 wire gr=state==0 && rn>0 && (!(an>0 && wn>0) || pref);
 wire gw=state==0 && an>0 && wn>0 && !gr;
 wire cb=state==2 && pready && pwrite;
 wire cr=state==2 && pready && !pwrite;
 assign s_awready=rst_n && ac<D;
 assign s_wready=rst_n && wc<D;
 assign s_arready=rst_n && rc<D;
 assign s_bvalid=rst_n && bn>0;
 assign s_rvalid=rst_n && xn>0;
 assign s_bresp=bq[0];assign s_rresp=rrq[0];assign s_rdata=rdq[0];
 assign psel=state!=0;assign penable=state==2;assign pprot=0;
 always_ff @(posedge clk) begin
  if(!rst_n) begin
   ac<=0;wc<=0;rc<=0;an<=0;wn<=0;rn<=0;bn<=0;xn<=0;state<=0;pref<=1;
   paddr<=0;pwdata<=0;pstrb<=0;pwrite<=0;
  end else begin
   ac<=ac+ap-bp;wc<=wc+wp-bp;rc<=rc+rp-xp;
   an<=an+ap-gw;wn<=wn+wp-gw;rn<=rn+rp-gr;
   bn<=bn+cb-bp;xn<=xn+cr-xp;
   if(gw) for(integer i=0;i<D-1;i++)begin aq[i]<=aq[i+1];wq[i]<=wq[i+1];sq[i]<=sq[i+1];end
   if(gr) for(integer i=0;i<D-1;i++)rq[i]<=rq[i+1];
   if(bp) for(integer i=0;i<D-1;i++)bq[i]<=bq[i+1];
   if(xp) for(integer i=0;i<D-1;i++)begin rdq[i]<=rdq[i+1];rrq[i]<=rrq[i+1];end
   if(ap) begin aq[an-gw]<=s_awaddr;end
   if(wp) begin wq[wn-gw]<=s_wdata;sq[wn-gw]<=s_wstrb;end
   if(rp) begin rq[rn-gr]<=s_araddr;end
   if(gw) begin
    paddr<=aq[0];pwdata<=wq[0];pstrb<=sq[0];pwrite<=1;
    pref<=1;state<=1;
   end else if(gr) begin
    paddr<=rq[0];pwdata<=0;pstrb<=0;pwrite<=0;
    pref<=0;state<=1;
   end
   if(state==1) state<=2;
   if(state==2 && pready) state<=0;
   if(cb) begin bq[bn-bp]<=pslverr?2:0;end
   if(cr) begin rrq[xn-xp]<=pslverr?2:0;rdq[xn-xp]<=prdata;end
  end
 end
endmodule
