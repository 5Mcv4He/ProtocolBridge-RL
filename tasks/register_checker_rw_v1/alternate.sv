module register_checker(input logic clk,rst_n,event_valid,is_write,
 input logic [3:0] address,input logic [7:0] write_data,read_data,
 output logic error);
logic [15:0] bad;
 assign error=|bad;
 genvar k;
 generate for(k=0;k<16;k=k+1)begin: cell_model
 logic [7:0] value;
 always @(posedge clk)begin
  if(!rst_n)begin value<=8'h00;bad[k]<=0;end
  else if(!error && event_valid && address==k)begin
   if(is_write) value<=write_data;
   else if(read_data!=value)bad[k]<=1;
  end
 end
 end endgenerate
endmodule
