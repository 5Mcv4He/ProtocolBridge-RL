module swd_read(input wire clk,rst_n,swclk,swdio,input wire [31:0] read_value,output reg dout,oe);
reg ck; reg [7:0] header; integer state,idx,ones; reg [31:0] data;
always @(posedge clk) begin
 ck<=swclk;
 if(!rst_n)begin ck<=0;header<=0;state<=0;idx<=0;ones<=0;oe<=0;dout<=0;data<=0;end
 else if(swclk&&!ck)begin
  if(!oe && swdio)begin if(ones<63)ones<=ones+1;end else ones<=0;
  if(ones>=49 && swdio && !oe)begin state<=0;oe<=0;end
  else case(state)
   0:if(!swdio)state<=1;
   1:if(swdio)begin header<=1;idx<=1;state<=2;end
   2:begin header[idx]<=swdio;if(idx==7)begin
    if({swdio,header[6:0]}==8'ha5)begin state<=3;idx<=0;data<=read_value;end else state<=1;
   end else idx<=idx+1;end
   3:begin state<=4;idx<=0;end
   4:begin oe<=1;dout<=idx==0;if(idx==2)begin state<=5;idx<=0;end else idx<=idx+1;end
   5:begin oe<=1;dout<=read_value[idx];if(idx==31)state<=6;else idx<=idx+1;end
   6:begin dout<=^data;state<=7;end
   7:begin oe<=0;state<=1;end
  endcase
 end
end
endmodule
