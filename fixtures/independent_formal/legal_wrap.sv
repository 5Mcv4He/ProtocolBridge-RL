module accumulator(input logic clk,rst_n,load,enable,input logic [7:0] value,output logic [7:0] q);
  always_ff @(posedge clk) begin
    casez ({rst_n,load,enable})
      3'b0??: q<=0;
      3'b11?: q<=value;
      3'b101: q<=q+value;
      default: q<=q;
    endcase
  end
endmodule
