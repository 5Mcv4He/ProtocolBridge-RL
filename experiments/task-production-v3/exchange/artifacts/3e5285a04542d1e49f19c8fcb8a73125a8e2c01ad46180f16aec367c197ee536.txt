module bitfold(input logic [7:0] data,output logic [3:0] result);
 logic[7:0] work;always_comb begin work=data;result=0;while(work!=0)begin work=work&(work-1);result=result+1;end end
endmodule
