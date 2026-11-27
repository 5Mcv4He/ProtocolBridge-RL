module uart_tx(input logic clk,rst_n,valid,input logic [7:0] data,
               output logic ready,tx);
  logic [10:0] frame;
  logic [3:0] tick;
  logic [7:0] count; // bit index / counter
  logic busy;
  // frame bit index: 0=start,1..8=data,9=parity,10=stop
  logic [3:0] bit_idx;
  assign ready = ~busy;
  assign tx = busy ? frame[bit_idx] : 1'b1;

  always_ff @(posedge clk) begin
    if (!rst_n) begin
      busy <= 1'b0;
      frame <= 11'h7FF;
      bit_idx <= 4'd0;
      tick <= 4'd0;
    end else if (!busy) begin
      tick <= 4'd0;
      bit_idx <= 4'd0;
      if (valid) begin
        busy <= 1'b1;
        frame <= {1'b1, ^data, data, 1'b0};
        bit_idx <= 4'd0;
        tick <= 4'd0;
      end
    end else begin
      if (tick == 4'd15) begin
        tick <= 4'd0;
        if (bit_idx == 4'd10) begin
          busy <= 1'b0;
          bit_idx <= 4'd0;
        end else begin
          bit_idx <= bit_idx + 4'd1;
        end
      end else begin
        tick <= tick + 4'd1;
      end
    end
  end
endmodule
