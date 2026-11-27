module uart_tx(input logic clk,rst_n,valid,input logic [7:0] data,
               output logic ready,tx);
  logic [10:0] frame;
  logic [7:0] cycles_left;
  assign ready=(cycles_left==0);
  assign tx=ready ? 1'b1 : frame[0];
  always_ff @(posedge clk) begin
    if(!rst_n) begin cycles_left<=0;frame<='1;end
    else if(ready) begin
      if(valid) begin frame<={1'b1,^data,data,1'b0};cycles_left<=176;end
    end else begin
      cycles_left<=cycles_left-1'b1;
      if(cycles_left[3:0]==1)frame<={1'b1,frame[10:1]};
    end
  end
endmodule
