module fifo_checker(input logic clk,rst_n,push,pop,
 input logic [7:0] push_id,pop_id,output logic error);
  integer count;
  logic [7:0] entries [0:2];
  integer i;
  always_ff @(posedge clk) begin
    if(!rst_n) begin count<=0;error<=0;end
    else if(!error) begin
      if((pop && count==0) || (push && count==3 && !pop) ||
         (pop && count>0 && pop_id!=entries[0])) error<=1;
      else begin
        if(pop) for(i=0;i<2;i=i+1)entries[i]<=entries[i+1];
        if(push)entries[count-(pop?1:0)]<=push_id;
        case({push,pop})
          2'b10:count<=count+1;
          2'b01:count<=count-1;
          default:count<=count;
        endcase
      end
    end
  end
endmodule
