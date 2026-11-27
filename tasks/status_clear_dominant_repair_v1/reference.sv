module status_register(input logic clk,rst_n,sw_write,input logic [7:0] hw_set,sw_data,output logic [7:0] status);
always_ff @(posedge clk) begin
 if(!rst_n) status<=0;
 else status<=(status | hw_set) & ~(sw_write ? sw_data : 8'b0);
end
endmodule
