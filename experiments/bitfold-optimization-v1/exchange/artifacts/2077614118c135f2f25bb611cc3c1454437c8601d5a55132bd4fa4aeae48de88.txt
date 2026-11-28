module bitfold(input logic [7:0] data,output logic [3:0] result);
logic [3:0] p1;
logic [4:0] r;
always_comb begin
  for (int i = 0; i < 4; i++) begin
    p1[i] = data[2*i] & data[2*i+1];
  end
  r = {1'b0, data[7:1] & 7'b1010101}
    + {2'b0, data[6:0] & 7'b1010101}
    + {2'b0, p1[3:1]} + {2'b0, p1[2:0]}
    + {1'b0, p1[3:1]} + {1'b0, p1[2:0]};
  result = r[3:0];
end
endmodule
