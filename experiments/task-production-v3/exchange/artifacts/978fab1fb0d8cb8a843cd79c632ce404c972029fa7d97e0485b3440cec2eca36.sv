module bitfold(input logic [7:0] data,output logic [3:0] result);
  always_comb begin
    result = 4'd0;
    for (int i = 0; i < 8; i++) begin
      result = result + data[i];
    end
  end
endmodule
