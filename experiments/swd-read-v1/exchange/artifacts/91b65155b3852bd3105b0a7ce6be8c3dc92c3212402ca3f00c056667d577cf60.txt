module swd_read(input wire clk,rst_n,swclk,swdio,input wire [31:0] read_value,output wire dout,oe);

  reg swclk_q;
  reg [3:0] bitcnt;
  reg req_active;
  reg in_txn;
  reg [5:0] phase;       // 0 = idle, 1..39 counting rising edges from Park
  reg [31:0] data_sh;
  reg par_r;
  reg dout_r, oe_r;

  assign dout = dout_r;
  assign oe = oe_r;

  wire rise  = swclk & ~swclk_q;
  wire fall  = ~swclk & swclk_q;

  always @(posedge clk) begin
    if (!rst_n) begin
      swclk_q <= 1'b0;
      bitcnt <= 4'd0;
      req_active <= 1'b0;
      in_txn <= 1'b0;
      phase <= 6'd0;
      data_sh <= 32'd0;
      par_r <= 1'b0;
      dout_r <= 1'b0;
      oe_r <= 1'b0;
    end else begin
      swclk_q <= swclk;

      if (fall) begin
        oe_r <= 1'b0;
        dout_r <= 1'b0;
      end

      if (rise) begin
        if (!in_txn) begin
          if (!req_active) begin
            if (swdio) begin
              req_active <= 1'b1;
              bitcnt <= 4'd1;
            end
          end else if (bitcnt == 4'd7) begin
            req_active <= 1'b0;
            bitcnt <= 4'd0;
            in_txn <= 1'b1;
            phase <= 6'd1;
            data_sh <= read_value;
            par_r <= ^read_value;
            oe_r <= 1'b0;
            dout_r <= 1'b0;
          end else begin
            bitcnt <= bitcnt + 4'd1;
          end
        end else begin
          case (phase)
            6'd2: begin
              oe_r <= 1'b1;
              dout_r <= 1'b1;
            end
            6'd1, 6'd3, 6'd4: begin
              oe_r <= 1'b1;
              dout_r <= 1'b0;
            end
            6'd5, 6'd6, 6'd7, 6'd8, 6'd9,
            6'd10, 6'd11, 6'd12, 6'd13, 6'd14,
            6'd15, 6'd16, 6'd17, 6'd18, 6'd19,
            6'd20, 6'd21, 6'd22, 6'd23, 6'd24,
            6'd25, 6'd26, 6'd27, 6'd28, 6'd29,
            6'd30, 6'd31, 6'd32, 6'd33, 6'd34,
            6'd35, 6'd36: begin
              oe_r <= 1'b1;
              dout_r <= data_sh[0];
              data_sh <= {1'b0, data_sh[31:1]};
            end
            6'd37: begin
              oe_r <= 1'b1;
              dout_r <= par_r;
            end
            default: begin
              oe_r <= 1'b0;
              dout_r <= 1'b0;
              in_txn <= 1'b0;
            end
          endcase
          phase <= phase + 6'd1;
        end
      end
    end
  end
endmodule
