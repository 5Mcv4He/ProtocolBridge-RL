module bitfold(input logic [7:0] data,output logic [3:0] result);
 always_comb result={3'b0,data[0]}+{3'b0,data[1]}+{3'b0,data[2]}+{3'b0,data[3]}+{3'b0,data[4]}+{3'b0,data[5]}+{3'b0,data[6]}+{3'b0,data[7]};
endmodule
