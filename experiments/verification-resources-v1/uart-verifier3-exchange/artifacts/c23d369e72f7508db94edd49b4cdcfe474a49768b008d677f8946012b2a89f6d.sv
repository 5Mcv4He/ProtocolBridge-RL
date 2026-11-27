module uart_tx(input logic clk,rst_n,valid,input logic [7:0] data,
               output logic ready,tx);
  logic [9:0] frame;
  logic [3:0] bit_cnt, tick;
  logic busy;

  assign ready = ~busy;
  assign tx = busy ? frame[0] : 1'b1;

  always_ff @(posedge clk) begin
    if (!rst_n) begin
      frame   <= 10'h3FF;
      bit_cnt <= 4'd0;
      tick    <= 4'd0;
      busy    <= 1'b0;
    end else if (!busy) begin
      if (valid) begin
        frame   <= {1'b1, data[7:0], 1'b0};
        bit_cnt <= 4'd9;
        tick    <= 4'd0;
        busy    <= 1'b1;
      end
    end else begin
      if (tick == 4'd15) begin
        tick <= 4'd0;
        if (bit_cnt == 4'd0) begin
          busy <= 1'b0;
          frame <= 10'h3FF;
        end else begin
          bit_cnt <= bit_cnt - 4'd1;
          frame <= {1'b1, frame[9:1]};
        end
      end else begin
        tick <= tick + 4'd1;
      end
    end
  end
endmodule
