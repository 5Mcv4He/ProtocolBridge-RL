module fifo_checker(input logic clk,rst_n,push,pop,
 input logic [7:0] push_id,pop_id,output logic error);
  always_ff @(posedge clk) error<=1'b0;
endmodule
