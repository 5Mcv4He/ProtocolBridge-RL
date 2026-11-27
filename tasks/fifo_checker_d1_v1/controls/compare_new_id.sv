module fifo_checker(input logic clk,rst_n,push,pop,
 input logic [7:0] push_id,pop_id,output logic error);
  integer count;
  logic [7:0] entries [0:0];
  integer head,tail;
  always_ff @(posedge clk) begin
    if(!rst_n) begin count<=0;head<=0;tail<=0;error<=0;end
    else if(!error) begin
      if((pop && count==0) || (push && count==1 && !pop) ||
         (pop && count>0 && pop_id!=push_id)) error<=1;
      else begin
        if(push) begin entries[tail]<=push_id;tail<=(tail==0)?0:tail+1;end
        if(pop)head<=(head==0)?0:head+1;
        case({push,pop})
          2'b10:count<=count+1;
          2'b01:count<=count-1;
          default:count<=count;
        endcase
      end
    end
  end
endmodule
