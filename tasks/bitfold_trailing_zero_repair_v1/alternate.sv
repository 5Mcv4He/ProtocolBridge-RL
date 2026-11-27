module bitfold(input logic [7:0] data,output logic [3:0] result);
 always_comb begin result=8;for(integer i=7;i>=0;i=i-1)if(data[i])result=i;end
endmodule
