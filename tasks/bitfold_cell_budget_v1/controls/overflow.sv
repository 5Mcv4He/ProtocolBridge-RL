module bitfold(input logic [7:0] data,output logic [3:0] result);
wire [1:0] a,b,c,d;wire [2:0] ab,cd;
assign a={1'b0,data[0]}+{1'b0,data[1]};assign b={1'b0,data[2]}+{1'b0,data[3]};
assign c={1'b0,data[4]}+{1'b0,data[5]};assign d={1'b0,data[6]}+{1'b0,data[7]};
assign ab={1'b0,a}+{1'b0,b};assign cd={1'b0,c}+{1'b0,d};
wire [2:0] truncated;assign result={1'b0,truncated};assign truncated={1'b0,ab}+{1'b0,cd};endmodule
