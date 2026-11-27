module bitfold(input logic [7:0] data,output logic [3:0] result);
always_latch if(data!=0) result=data[3:0];endmodule
