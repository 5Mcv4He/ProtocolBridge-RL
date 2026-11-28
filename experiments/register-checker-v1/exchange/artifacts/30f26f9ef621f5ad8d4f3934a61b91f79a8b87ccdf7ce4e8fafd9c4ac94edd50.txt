module register_checker(input logic clk,rst_n,event_valid,is_write,
 input logic [3:0] address,input logic [7:0] write_data,read_data,
 output logic error);
 logic [7:0] mem[16];
 logic err;
 integer i;
 always_ff @(posedge clk) begin
   if(!rst_n) begin
     for(i=0;i<16;i=i+1) mem[i]<=8'd0;
     err<=1'b0;
   end else if(event_valid) begin
     if(is_write) mem[address]<=write_data;
     else if(read_data!==mem[address]) err<=1'b1;
   end
 end
 assign error=err;
endmodule
