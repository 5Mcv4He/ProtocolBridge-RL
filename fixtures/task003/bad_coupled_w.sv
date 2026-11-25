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
 typedef enum logic [2:0] {IDLE,SETUP,ACCESS,RESP} state_t;
 state_t state;
 logic [31:0] aq[0:1],dq[0:1],rq[0:1];
 logic [3:0] sq[0:1];
 logic awp,wp,rp,arp,wrp,rrp;
 logic [1:0] ac,wc,rc;
 logic prefer_read;
 wire apush=s_awvalid && s_awready;
 wire wpush=s_wvalid && s_wready;
 wire rpush=s_arvalid && s_arready;
 wire bpop=s_bvalid && s_bready;
 wire rpop=s_rvalid && s_rready;
 assign s_awready=rst_n && ac<2;
 assign s_wready=rst_n && wc<2 && ac>0;
 assign s_arready=rst_n && rc<2;
 assign psel=state==SETUP || state==ACCESS;
 assign penable=state==ACCESS;
 assign pprot=0;
 always_ff @(posedge clk) begin
  if(!rst_n) begin
   state<=IDLE;ac<=0;wc<=0;rc<=0;
   awp<=0;wp<=0;rp<=0;arp<=0;wrp<=0;rrp<=0;prefer_read<=1;
   s_bvalid<=0;s_rvalid<=0;s_bresp<=0;s_rresp<=0;s_rdata<=0;
   paddr<=0;pwdata<=0;pstrb<=0;pwrite<=0;
  end else begin
   if(apush) begin aq[awp]<=s_awaddr;awp<=!awp;end
   if(wpush) begin dq[wp]<=s_wdata;sq[wp]<=s_wstrb;wp<=!wp;end
   if(rpush) begin rq[rp]<=s_araddr;rp<=!rp;end
   if(bpop) begin arp<=!arp;wrp<=!wrp;end
   if(rpop) rrp<=!rrp;
   case({apush,bpop}) 2'b10:ac<=ac+1;2'b01:ac<=ac-1;default:ac<=ac;endcase
   case({wpush,bpop}) 2'b10:wc<=wc+1;2'b01:wc<=wc-1;default:wc<=wc;endcase
   case({rpush,rpop}) 2'b10:rc<=rc+1;2'b01:rc<=rc-1;default:rc<=rc;endcase
   case(state)
    IDLE: begin
     if(rc>0 && (!(ac>0 && wc>0) || prefer_read)) begin
      paddr<=rq[rrp];pwdata<=0;pstrb<=0;pwrite<=0;prefer_read<=0;state<=SETUP;
     end else if(ac>0 && wc>0) begin
      paddr<=aq[arp];pwdata<=dq[wrp];pstrb<=sq[wrp];pwrite<=1;prefer_read<=1;state<=SETUP;
     end
    end
    SETUP:state<=ACCESS;
    ACCESS:if(pready) begin
     if(pwrite) begin s_bresp<=pslverr?2'b10:2'b00;s_bvalid<=1;end
     else begin s_rresp<=pslverr?2'b10:2'b00;s_rdata<=prdata;s_rvalid<=1;end
     state<=RESP;
    end
    RESP:if(bpop || rpop) begin s_bvalid<=0;s_rvalid<=0;state<=IDLE;end
    default:state<=IDLE;
   endcase
  end
 end
endmodule
