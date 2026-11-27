module uart_tx(input logic clk,rst_n,valid,input logic [7:0] data,
               output logic ready,tx);
  logic [9:0] frame;
  logic [3:0] remaining,tick;
  assign ready=(remaining==0);
  assign tx=ready ? 1'b1 : frame[0];
  always_ff @(posedge clk) begin
    if (!rst_n) begin frame<='1; remaining<=0; tick<=0; end
    else if (ready) begin
      if (valid) begin frame<={1'b1,data,1'b0};remaining<=10;tick<=0;end
    end else if (tick==15) begin
      frame<={1'b1,frame[9:1]};remaining<=remaining-1'b1;tick<=0;
      // Injected defect: accept before pre-edge ready is high.
      if (remaining==1 && valid) begin frame<={1'b1,data,1'b0};remaining<=10; end
    end else tick<=tick+1'b1;
  end
endmodule
