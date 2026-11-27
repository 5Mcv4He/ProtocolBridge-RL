module uart_tx(input logic clk,rst_n,valid,input logic [7:0] data,
               output logic ready,tx);
  logic [9:0] frame;
  logic [3:0] remaining,tick;

  always_ff @(posedge clk) begin
    if (!rst_n) begin
      frame     <= 10'h3FF;
      remaining <= 4'd0;
      tick      <= 4'd0;
    end else if (remaining == 4'd0) begin
      tick <= 4'd0;
      if (valid) begin
        frame     <= {1'b1, data, 1'b0};
        remaining <= 4'd10;
      end
    end else begin
      if (tick == 4'd15) begin
        tick      <= 4'd0;
        frame     <= {1'b1, frame[9:1]};
        remaining <= remaining - 4'd1;
      end else begin
        tick <= tick + 4'd1;
      end
    end
  end

  assign ready = (remaining == 4'd0);
  assign tx = (remaining == 4'd0) ? (valid ? 1'b0 : 1'b1) : frame[0];
endmodule
