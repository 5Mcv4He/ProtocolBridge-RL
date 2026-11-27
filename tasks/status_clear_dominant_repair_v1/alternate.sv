module status_register(input logic clk,rst_n,sw_write,input logic [7:0] hw_set,sw_data,output logic [7:0] status);
always_ff @(posedge clk) begin
 if(!rst_n) status<=0;
 else for(integer i=0;i<8;i=i+1) begin if(sw_write && sw_data[i]) status[i]<=0; else if(hw_set[i]) status[i]<=1; end
end
endmodule
