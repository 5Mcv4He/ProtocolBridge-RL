module fifo_checker(input logic clk,rst_n,push,pop,
 input logic [7:0] push_id,pop_id,output logic error);

  logic [7:0] q [0:4];
  logic [2:0] head, tail, count;
  logic bad;

  always_comb begin
    bad = 1'b0;
    if (!error) begin
      if (pop && (count == 0 || pop_id != q[head]))
        bad = 1'b1;
      else if (push && count == 5 && !pop)
        bad = 1'b1;
    end
  end

  always_ff @(posedge clk) begin
    if (!rst_n) begin
      error <= 1'b0;
      head <= 3'd0;
      tail <= 3'd0;
      count <= 3'd0;
    end else if (error) begin
      error <= 1'b1;
    end else if (bad) begin
      error <= 1'b1;
    end else begin
      error <= 1'b0;
      if (pop && push) begin
        q[tail] <= push_id;
        head <= (head == 3'd4) ? 3'd0 : head + 3'd1;
        tail <= (tail == 3'd4) ? 3'd0 : tail + 3'd1;
      end else if (pop) begin
        head <= (head == 3'd4) ? 3'd0 : head + 3'd1;
        count <= count - 3'd1;
      end else if (push) begin
        q[tail] <= push_id;
        tail <= (tail == 3'd4) ? 3'd0 : tail + 3'd1;
        count <= count + 3'd1;
      end
    end
  end

endmodule
