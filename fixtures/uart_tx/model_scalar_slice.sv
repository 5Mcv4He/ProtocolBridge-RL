module uart_tx(input logic clk,rst_n,valid,data,
               output logic ready,tx);
  logic [7:0] shifter;
  logic [3:0] bit_cnt;
  logic [3:0] cyc_cnt;
  logic busy;
  logic [7:0] latched;

  assign ready = ~busy;
  assign tx = busy ? shifter[0] : 1'b1;

  always_ff @(posedge clk) begin
    if (!rst_n) begin
      shifter <= 8'hFF;
      latched <= 8'h00;
      bit_cnt <= 4'd0;
      cyc_cnt <= 4'd0;
      busy <= 1'b0;
    end else if (!busy) begin
      if (valid) begin
        latched <= data;
        shifter <= {1'b0, data[7:1]};
        bit_cnt <= 4'd0;
        cyc_cnt <= 4'd0;
        busy <= 1'b1;
      end
    end else begin
      if (cyc_cnt == 4'd15) begin
        cyc_cnt <= 4'd0;
        if (bit_cnt == 4'd0) begin
          shifter <= {latched[7], latched[7:1]};
          bit_cnt <= 4'd1;
        end else if (bit_cnt <= 4'd8) begin
          shifter <= {^latched, shifter[7:1]};
          bit_cnt <= 4'd9;
        end else if (bit_cnt == 4'd9) begin
          shifter <= 8'hFF;
          bit_cnt <= 4'd10;
        end else begin
          busy <= 1'b0;
        end
      end else begin
        cyc_cnt <= cyc_cnt + 4'd1;
      end
    end
  end
endmodule
