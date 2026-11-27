module uart_tx(input logic clk,rst_n,valid,input logic [7:0] data,
               output logic ready,tx);
  logic [15:0] counter;
  logic [3:0] bit_idx;
  logic [9:0] shifter;
  logic active;

  assign ready = ~active;
  assign tx = active ? shifter[0] : 1'b1;

  always_ff @(posedge clk) begin
    if (!rst_n) begin
      active  <= 1'b0;
      counter <= 16'd0;
      bit_idx <= 4'd0;
      shifter <= 10'h3FF;
    end else if (!active) begin
      if (valid) begin
        active  <= 1'b1;
        counter <= 16'd0;
        bit_idx <= 4'd0;
        shifter <= {1'b1, data, 1'b0};
      end
    end else begin
      if (counter == 16'd15) begin
        counter <= 16'd0;
        if (bit_idx == 4'd9) begin
          active <= 1'b0;
        end else begin
          shifter <= {1'b1, shifter[9:1]};
          bit_idx <= bit_idx + 4'd1;
        end
      end else begin
        counter <= counter + 16'd1;
      end
    end
  end
endmodule
