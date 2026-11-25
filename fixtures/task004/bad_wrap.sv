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
 integer at,wt,rt,ah,wh,rh,bt,bh,xt,xh;
 integer ac,wc,rc,an,wn,rn,bn,xn;
 logic pref;
 logic [1:0] state;
 wire ap=s_awvalid && s_awready,wp=s_wvalid && s_wready,rp=s_arvalid && s_arready;
 wire bp=s_bvalid && s_bready,xp=s_rvalid && s_rready;
 wire gr=state==0 && rn>0 && (!(an>0 && wn>0) || pref);
 wire gw=state==0 && an>0 && wn>0 && !gr;
 wire cb=state==2 && pready && pwrite;
 wire cr=state==2 && pready && !pwrite;
 function automatic integer inc(input integer v);inc=v==D?0:v+1;endfunction
 assign s_awready=rst_n && ac<D;
 assign s_wready=rst_n && wc<D;
 assign s_arready=rst_n && rc<D;
 assign s_bvalid=rst_n && bn>0;
 assign s_rvalid=rst_n && xn>0;
 assign s_bresp=bq[bh];assign s_rresp=rrq[xh];assign s_rdata=rdq[xh];
 assign psel=state!=0;assign penable=state==2;assign pprot=0;
 always_ff @(posedge clk) begin
  if(!rst_n) begin
   at<=0;wt<=0;rt<=0;ah<=0;wh<=0;rh<=0;bt<=0;bh<=0;xt<=0;xh<=0;
   ac<=0;wc<=0;rc<=0;an<=0;wn<=0;rn<=0;bn<=0;xn<=0;state<=0;pref<=1;
   paddr<=0;pwdata<=0;pstrb<=0;pwrite<=0;
  end else begin
   ac<=ac+ap-bp;wc<=wc+wp-bp;rc<=rc+rp-xp;
   an<=an+ap-gw;wn<=wn+wp-gw;rn<=rn+rp-gr;
   bn<=bn+cb-bp;xn<=xn+cr-xp;
   if(ap) begin aq[at]<=s_awaddr;at<=inc(at);end
   if(wp) begin wq[wt]<=s_wdata;sq[wt]<=s_wstrb;wt<=inc(wt);end
   if(rp) begin rq[rt]<=s_araddr;rt<=inc(rt);end
   if(gw) begin
    paddr<=aq[ah];pwdata<=wq[wh];pstrb<=sq[wh];pwrite<=1;
    ah<=inc(ah);wh<=inc(wh);pref<=1;state<=1;
   end else if(gr) begin
    paddr<=rq[rh];pwdata<=0;pstrb<=0;pwrite<=0;
    rh<=inc(rh);pref<=0;state<=1;
   end
   if(state==1) state<=2;
   if(state==2 && pready) state<=0;
   if(cb) begin bq[bt]<=pslverr?2:0;bt<=inc(bt);end
   if(cr) begin rrq[xt]<=pslverr?2:0;rdq[xt]<=prdata;xt<=inc(xt);end
   if(bp) bh<=inc(bh);
   if(xp) xh<=inc(xh);
  end
 end
endmodule
