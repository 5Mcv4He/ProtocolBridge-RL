module bitfold(input logic [7:0] data,output logic [3:0] result);
wire [7:0] a,b,c;
assign a=data-((data>>1)&8'h55);
assign b=(a&8'h33)+((a>>2)&8'h33);
assign c=(b+(b>>4))&8'h0f;
assign result=c[3:0];endmodule
