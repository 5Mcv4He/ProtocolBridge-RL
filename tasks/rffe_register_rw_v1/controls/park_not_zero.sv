module rffe_register(input logic clk,rst_n,sclk,sdata,output logic sdata_out,sdata_oe);
 logic cs1,cs2,csd,ds1,ds2,dsd,armed;logic[12:0] command;logic[8:0] payload;
 logic[7:0] regs[0:31];logic[4:0] address;logic[8:0] response;integer state,n,i;
 wire rise=cs2&&!csd,fall=!cs2&&csd;
 always_ff @(posedge clk) begin
  if(!rst_n)begin cs1<=0;cs2<=0;csd<=0;ds1<=0;ds2<=0;dsd<=0;armed<=0;state<=0;n<=0;command<=0;payload<=0;sdata_out<=0;sdata_oe<=0;address<=0;response<=0;for(i=0;i<32;i=i+1)regs[i]<=8'h00;end
  else begin
   cs1<=sclk;cs2<=cs1;csd<=cs2;ds1<=sdata;ds2<=ds1;dsd<=ds2;
   case(state)
    0:begin sdata_oe<=0;if(!cs2&&ds2&&!dsd)armed<=1;if(!cs2&&!ds2&&dsd&&armed)begin state<=1;n<=0;command<=0;armed<=0;end end
    1:if(fall)begin command<={command[11:0],ds2};if(n==12)begin address<=command[4:0];n<=0;if(command[11:8]==1 && (^{command[11:0],ds2}))begin if(command[7:5]==2)begin state<=2;payload<=0;end else if(command[7:5]==3)begin state<=3;response<={regs[command[4:0]],~^regs[command[4:0]]};end else state<=0;end else state<=0;end else n<=n+1;end
    2:if(fall)begin payload<={payload[7:0],ds2};if(n==8)begin if(^{payload[7:0],ds2})regs[address]<=payload[7:0];state<=6;n<=0;end else n<=n+1;end
    3:if(fall)begin state<=4;n<=0;end
    4:begin if(rise)begin sdata_oe<=1;sdata_out<=response[8-n];end if(fall)begin if(n==8)begin state<=5;n<=0;sdata_out<=1;end else n<=n+1;end end
    5:begin if(rise)begin sdata_out<=1;sdata_oe<=1;end if(fall)begin sdata_oe<=0;state<=0;armed<=0;end end
    6:if(fall)begin state<=0;armed<=0;end
    7:if(fall)begin sdata_oe<=0;state<=0;armed<=0;end
   endcase
  end
 end
endmodule
