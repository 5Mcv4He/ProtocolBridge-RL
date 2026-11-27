module status_register (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       sw_write,
    input  wire [7:0] hw_set,
    input  wire [7:0] sw_data,
    output reg  [7:0] status
);
    integer i;
    always @(posedge clk) begin
        if (!rst_n) begin
            status <= 8'b0;
        end else begin
            for (i = 0; i < 8; i = i + 1) begin
                if (hw_set[i])
                    status[i] <= 1'b1;
                else if (sw_write && sw_data[i])
                    status[i] <= 1'b0;
            end
        end
    end
endmodule
