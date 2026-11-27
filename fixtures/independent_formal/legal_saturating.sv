module accumulator(input logic clk,rst_n,load,enable,input logic [7:0] value,output logic [7:0] q);
  always_ff @(posedge clk) begin
    if (!rst_n) q<=0;
    else if(load) q<=value;
    else if(enable) begin
      if(q > (8'hff-value)) q<=8'hff;
      else q<=q+value;
    end
  end
endmodule
