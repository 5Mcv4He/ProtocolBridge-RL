`timescale 1ns/1ps
// Independent integer transition oracle; never supplied to the solver.
module tb;
  bit clk=0; always #5 clk=~clk;
  logic rst_n=0,load=0,enable=0;
  logic [7:0] value=0,q;
  accumulator dut(.*);
  integer expected=0,checked=0,mode=0,total;
  task step(input bit reset_value,input bit load_value,input bit enable_value,input integer operand);
    @(negedge clk);rst_n=reset_value;load=load_value;enable=enable_value;value=operand;
    if(!reset_value) expected=0;
    else if(load_value) expected=operand;
    else if(enable_value) begin
      total=expected+operand;
      if(mode && total>255) expected=255;
      else expected=total%256;
    end
    @(posedge clk);#1;
    if(q!==expected[7:0]) begin $display("PB_ANCHOR_FAIL checked=%0d",checked);$finish;end
    checked++;
  endtask
  initial begin
    if(!$value$plusargs("mode=%d",mode)) mode=0;
    step(0,1,1,255);
    for(integer state_value=0;state_value<256;state_value++) begin
      for(integer operand=0;operand<256;operand++) begin
        step(1,1,1,state_value);
        step(1,0,1,operand);
        step(1,0,0,255-operand);
      end
    end
    step(1,1,0,73);
    @(negedge clk);rst_n=0;#1;
    if(q!==8'd73) begin $display("PB_ANCHOR_ASYNC_RESET");$finish;end
    @(posedge clk);#1;
    if(q!==8'd0) begin $display("PB_ANCHOR_RESET_FAIL");$finish;end
    $display("PB_ANCHOR_PASS checked=%0d state_operand_pairs=65536",checked);
    $finish;
  end
  initial begin #10000000;$display("PB_ANCHOR_TIMEOUT");$finish;end
endmodule
