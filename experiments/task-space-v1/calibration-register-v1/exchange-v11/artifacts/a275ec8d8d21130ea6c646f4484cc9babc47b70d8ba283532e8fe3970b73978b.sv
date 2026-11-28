module bridge(
 input logic clk,rst_n,psel,penable,pwrite,
 input logic [31:0] paddr,pwdata,input logic [3:0] pstrb,
 output logic [31:0] prdata,output logic pready,pslverr
);
logic [1:0] wait_cnt;
logic [31:0] r0,r1,r2;
logic [31:0] rd_hold,err_hold;
logic active_done;

wire access = psel && penable;
wire is0 = (paddr == 32'h0000000c);
wire is1 = (paddr == 32'h00000020);
wire is2 = (paddr == 32'h00000030);

wire [31:0] mask0 = 32'hff00ffff;
wire [31:0] mask1 = 32'hffffffff;
wire [31:0] byteen = { {8{pstrb[3]}}, {8{pstrb[2]}}, {8{pstrb[1]}}, {8{pstrb[0]}} };
wire [31:0] wen0 = byteen & mask0;
wire [31:0] wen1 = byteen & mask1;

always_comb begin
  pready = 1'b0;
  if (access && wait_cnt == 2'd2) pready = 1'b1;
end

assign prdata = access ? rd_hold : 32'b0;
assign pslverr = access ? err_hold : 1'b0;

always_ff @(posedge clk) begin
  if (!rst_n) begin
    r0 <= 32'h12345678;
    r1 <= 32'hffff00ff;
    r2 <= 32'h55aa9966;
    wait_cnt <= 2'd0;
    rd_hold <= 32'b0;
    err_hold <= 1'b0;
  end else begin
    if (!access) begin
      wait_cnt <= 2'd0;
      rd_hold <= 32'b0;
      err_hold <= 1'b0;
    end else if (wait_cnt == 2'd2) begin
      wait_cnt <= 2'd0;
      if (pwrite) begin
        if (is0) begin
          r0 <= (r0 & ~wen0) | (pwdata & wen0);
        end else if (is1) begin
          r1 <= r1 & ~(pwdata & wen1);
        end
      end
    end else begin
      wait_cnt <= wait_cnt + 2'd1;
      if (wait_cnt == 2'd0) begin
        if (is0) begin
          rd_hold <= pwrite ? r0 : r0;
          err_hold <= 1'b0;
        end else if (is1) begin
          rd_hold <= r1;
          err_hold <= 1'b0;
        end else if (is2) begin
          rd_hold <= r2;
          err_hold <= 1'b0;
        end else begin
          rd_hold <= 32'b0;
          err_hold <= 1'b1;
        end
      end
    end
  end
end
endmodule
