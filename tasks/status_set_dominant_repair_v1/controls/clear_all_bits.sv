module status_register(input logic clk,rst_n,sw_write,input logic [7:0] hw_set,sw_data,output logic [7:0] status);
always_ff @(posedge clk) begin
 if(!rst_n) status<=0;
 else status<=(status & ~(sw_write ? 8'hff : 8'b0)) | hw_set;
end
endmodule
