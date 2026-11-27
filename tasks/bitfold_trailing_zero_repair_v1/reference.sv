module bitfold(input logic [7:0] data,output logic [3:0] result);
 always_comb begin casez(data)
 8'b???????1:result=0;8'b??????10:result=1;8'b?????100:result=2;8'b????1000:result=3;
 8'b???10000:result=4;8'b??100000:result=5;8'b?1000000:result=6;8'b10000000:result=7;default:result=8;endcase end
endmodule
