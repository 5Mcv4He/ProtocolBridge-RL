module bitfold(input logic [7:0] data,output logic [3:0] result);
 integer i;always_comb begin result=0;for(i=0;i<8;i=i+1)result=result+data[i];end
endmodule
