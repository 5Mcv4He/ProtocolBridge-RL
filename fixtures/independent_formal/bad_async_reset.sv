module accumulator(input logic clk,rst_n,load,enable,input logic [7:0] value,output logic [7:0] q);
  logic [8:0] sum;
  assign sum={1'b0,q}+{1'b0,value};
  always_ff @(posedge clk or negedge rst_n) begin
    if(!rst_n) q<=8'd0;
    else if(load) q<=value;
    else if(enable) q<=sum[7:0];
  end
endmodule
