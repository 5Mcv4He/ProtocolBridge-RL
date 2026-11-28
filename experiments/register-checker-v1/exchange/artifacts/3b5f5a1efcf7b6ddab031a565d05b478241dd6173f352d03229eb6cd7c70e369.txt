module register_checker(input logic clk,rst_n,event_valid,is_write,
 input logic [3:0] address,input logic [7:0] write_data,read_data,
 output logic error);
  logic [7:0] regs [16];
  integer i;
  always_ff @(posedge clk) begin
    if(!rst_n) begin
      for(i=0;i<16;i=i+1) regs[i] <= 8'hFF;
      error <= 1'b0;
    end else if(event_valid) begin
      if(is_write) begin
        regs[address] <= regs[address] & ~write_data;
      end else begin
        if(read_data !== regs[address]) error <= 1'b1;
      end
    end
  end
endmodule
