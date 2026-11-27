module fifo_checker(input logic clk,rst_n,push,pop,
 input logic [7:0] push_id,pop_id,output logic error);
  logic [7:0] q0,q1,q2;
  logic [1:0] cnt;
  logic err;
  wire full = (cnt==2'd3);
  wire empty = (cnt==2'd0);
  wire head_bad = pop && !empty && (pop_id != q0);
  wire bad = err || (pop && empty) || (push && full && !pop) || head_bad;
  always_ff @(posedge clk) begin
    if (!rst_n) begin
      err <= 1'b0; cnt <= 2'd0; q0 <= 8'd0; q1 <= 8'd0; q2 <= 8'd0;
    end else if (err) begin
      err <= 1'b1;
    end else if (bad) begin
      err <= 1'b1;
    end else if (pop && push) begin
      if (cnt==2'd1) begin q0 <= push_id; end
      else if (cnt==2'd2) begin q0 <= q1; q1 <= push_id; end
      else if (cnt==2'd3) begin q0 <= q1; q1 <= q2; q2 <= push_id; end
    end else if (push) begin
      if (cnt==2'd0) q0 <= push_id;
      else if (cnt==2'd1) q1 <= push_id;
      else if (cnt==2'd2) q2 <= push_id;
      cnt <= cnt + 2'd1;
    end else if (pop) begin
      if (cnt==2'd2) begin q0 <= q1; end
      else if (cnt==2'd3) begin q0 <= q1; q1 <= q2; end
      cnt <= cnt - 2'd1;
    end
  end
  assign error = err;
endmodule
