module i2c_sink(input logic clk,rst_n,scl,sda,output logic sda_drive_low,item_valid,output logic [15:0] item_data);
 always_ff @(posedge clk)begin sda_drive_low<=0;item_valid<=0;item_data<=0;end
endmodule
