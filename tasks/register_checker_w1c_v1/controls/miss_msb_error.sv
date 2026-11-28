module register_checker(input logic clk,rst_n,event_valid,is_write,
 input logic [3:0] address,input logic [7:0] write_data,read_data,
 output logic error);
logic [7:0] expected [0:15];integer i;
 always @(posedge clk) begin
  if(!rst_n)begin
   error<=0;
   for(i=0;i<16;i=i+1)expected[i]<=8'hff;
  end else if(!error && event_valid)begin
   if(is_write)expected[address]<=expected[address] & ~write_data;
   else if((read_data & 127)!=(expected[address] & 127))error<=1;
  end
 end
endmodule
