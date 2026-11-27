module uart_tx(input logic clk,rst_n,valid,input logic [7:0] data,
               output logic ready,tx);

  logic [10:0] frame;
  logic [3:0]  tick;      // 0..15 within current bit
  logic [3:0]  bits_left; // number of bits remaining in frame

  assign ready = (bits_left == 4'd0);
  assign tx    = ready ? 1'b1 : frame[0];

  always_ff @(posedge clk) begin
    if (!rst_n) begin
      frame     <= 11'h7FF;
      bits_left <= 4'd0;
      tick      <= 4'd0;
    end else if (ready) begin
      if (valid) begin
        // {stop, parity, data[7:0], start}
        frame     <= {1'b1, ^data, data, 1'b0};
        bits_left <= 11'd11;
        tick      <= 4'd0;
      end
    end else if (tick == 4'd15) begin
      frame     <= {1'b1, frame[10:1]};
      bits_left <= bits_left - 4'd1;
      tick      <= 4'd0;
    end else begin
      tick <= tick + 4'd1;
    end
  end

endmodule
