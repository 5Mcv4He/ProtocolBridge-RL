module bridge(
 input logic clk,rst_n,psel,penable,pwrite,
 input logic [31:0] paddr,pwdata,input logic [3:0] pstrb,
 output logic [31:0] prdata,output logic pready,pslverr
);
assign prdata=0;assign pready=0;assign pslverr=0;
endmodule
