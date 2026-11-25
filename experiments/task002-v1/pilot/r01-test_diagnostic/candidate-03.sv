module bridge(
 input logic clk,rst_n,
 input logic [31:0] s_awaddr, input logic s_awvalid, output logic s_awready,
 input logic [31:0] s_wdata, input logic [3:0] s_wstrb, input logic s_wvalid, output logic s_wready,
 output logic [1:0] s_bresp, output logic s_bvalid, input logic s_bready,
 input logic [31:0] s_araddr, input logic s_arvalid, output logic s_arready,
 output logic [31:0] s_rdata, output logic [1:0] s_rresp, output logic s_rvalid, input logic s_rready,
 output logic [31:0] paddr,pwdata, output logic [3:0] pstrb, output logic [2:0] pprot,
 output logic [2:0] psel, output logic penable,pwrite, input logic [95:0] prdata, input logic [2:0] pready,pslverr
);

 typedef enum logic [2:0] {
   IDLE,           // waiting for a request
   WR_WAIT,        // holding one write half, waiting for the other
   UNMAPPED_W,     // unmapped write: respond after absorbing both halves
   UNMAPPED_R,     // unmapped read response
   APB_SETUP,      // APB setup cycle
   APB_ACCESS,     // APB access, waiting pready
   RESP            // mapped response pending
 } state_t;

 state_t state, nstate;

 reg [31:0] aw_addr_q;
 reg [31:0] w_data_q;
 reg [3:0]  w_strb_q;
 reg [31:0] rd_addr_q;

 reg aw_got_q, w_got_q;

 reg [31:0] paddr_q;
 reg [31:0] pwdata_q;
 reg [3:0]  pstrb_q;
 reg        pwrite_q;
 reg [2:0]  psel_q;

 reg [1:0]  bresp_q;
 reg [31:0] rdata_q;
 reg [1:0]  rresp_q;

 // decode
 logic [2:0] dec_psel;
 logic       dec_map;
 logic [31:0] dec_addr;

 always_comb begin
   dec_map  = 1'b0;
   dec_psel = 3'b000;
   dec_addr = 32'h0;
   if (aw_addr_q >= 32'h00001000 && aw_addr_q <= 32'h00001fff) begin
     dec_map = 1'b1; dec_psel = 3'b001; dec_addr = aw_addr_q - 32'h00001000;
   end else if (aw_addr_q >= 32'h00008000 && aw_addr_q <= 32'h00009fff) begin
     dec_map = 1'b1; dec_psel = 3'b010; dec_addr = aw_addr_q - 32'h00008000;
   end else if (aw_addr_q >= 32'h40000000 && aw_addr_q <= 32'h40000fff) begin
     dec_map = 1'b1; dec_psel = 3'b100; dec_addr = aw_addr_q - 32'h40000000;
   end
 end

 logic [2:0] rd_psel;
 logic       rd_map;
 logic [31:0] rd_addr;

 always_comb begin
   rd_map  = 1'b0;
   rd_psel = 3'b000;
   rd_addr = 32'h0;
   if (rd_addr_q >= 32'h00001000 && rd_addr_q <= 32'h00001fff) begin
     rd_map = 1'b1; rd_psel = 3'b001; rd_addr = rd_addr_q - 32'h00001000;
   end else if (rd_addr_q >= 32'h00008000 && rd_addr_q <= 32'h00009fff) begin
     rd_map = 1'b1; rd_psel = 3'b010; rd_addr = rd_addr_q - 32'h00008000;
   end else if (rd_addr_q >= 32'h40000000 && rd_addr_q <= 32'h40000fff) begin
     rd_map = 1'b1; rd_psel = 3'b100; rd_addr = rd_addr_q - 32'h40000000;
   end
 end

 // next state
 always_comb begin
   nstate = state;
   case (state)
     IDLE: nstate = IDLE;
     WR_WAIT: begin
       if (aw_got_q && w_got_q) begin
         if (dec_map) nstate = APB_SETUP;
         else         nstate = UNMAPPED_W;
       end
     end
     UNMAPPED_W: nstate = RESP;
     UNMAPPED_R: nstate = RESP;
     APB_SETUP:  nstate = APB_ACCESS;
     APB_ACCESS: begin
       if (pready[psel_q]) nstate = RESP;
     end
     RESP: begin
       if (pwrite_q ? (s_bvalid && s_bready) : (s_rvalid && s_rready))
         nstate = IDLE;
     end
     default: nstate = IDLE;
   endcase
 end

 // outputs
 always_comb begin
   s_awready = 1'b0;
   s_wready  = 1'b0;
   s_arready = 1'b0;
   s_bvalid  = 1'b0;
   s_rvalid  = 1'b0;
   if (state == IDLE) s_arready = 1'b1;
   if (state == IDLE || state == WR_WAIT) begin
     if (!aw_got_q) s_awready = 1'b1;
     if (!w_got_q)  s_wready  = 1'b1;
   end
   if (state == RESP) begin
     if (pwrite_q) s_bvalid = 1'b1;
     else          s_rvalid = 1'b1;
   end

   psel    = psel_q;
   penable = (state == APB_ACCESS);
   paddr   = paddr_q;
   pwrite  = pwrite_q;
   pwdata  = pwdata_q;
   pstrb   = pstrb_q;
   pprot   = 3'b000;

   s_bresp = bresp_q;
   s_rresp = rresp_q;
   s_rdata = rdata_q;
 end

 // sequential
 always_ff @(posedge clk) begin
   if (!rst_n) begin
     state    <= IDLE;
     aw_addr_q <= 32'h0;
     w_data_q  <= 32'h0;
     w_strb_q  <= 4'h0;
     rd_addr_q <= 32'h0;
     aw_got_q  <= 1'b0;
     w_got_q   <= 1'b0;
     paddr_q   <= 32'h0;
     pwdata_q  <= 32'h0;
     pstrb_q   <= 4'h0;
     pwrite_q  <= 1'b0;
     psel_q    <= 3'b000;
     bresp_q   <= 2'b00;
     rdata_q   <= 32'h0;
     rresp_q   <= 2'b00;
   end else begin
     case (state)
       IDLE: begin
         // accept AR immediately (reads take priority for AR only when no write in progress)
         if (s_arvalid && !aw_got_q && !w_got_q) begin
           rd_addr_q <= s_araddr;
           if (rd_map_comb(s_araddr)) begin
             paddr_q  <= rd_local(s_araddr);
             pwrite_q <= 1'b0;
             pwdata_q <= 32'h0;
             pstrb_q  <= 4'h0;
             psel_q   <= rd_sel(s_araddr);
             state    <= APB_SETUP;
           end else begin
             pwrite_q <= 1'b0;
             rdata_q  <= 32'h0;
             rresp_q  <= 2'b11;
             state    <= UNMAPPED_R;
           end
         end else begin
           // accept write halves
           if (s_awvalid && !aw_got_q) begin
             aw_addr_q <= s_awaddr;
             aw_got_q  <= 1'b1;
           end
           if (s_wvalid && !w_got_q) begin
             w_data_q <= s_wdata;
             w_strb_q <= s_wstrb;
             w_got_q  <= 1'b1;
           end
           if ((aw_got_q || (s_awvalid && !aw_got_q)) && (w_got_q || (s_wvalid && !w_got_q))) begin
             // both halves now present; move on next cycle via WR_WAIT check
             state <= WR_WAIT;
           end
         end
       end
       WR_WAIT: begin
         if (aw_got_q && w_got_q) begin
           if (dec_map) begin
             paddr_q  <= dec_addr;
             pwrite_q <= 1'b1;
             pwdata_q <= w_data_q;
             pstrb_q  <= w_strb_q;
             psel_q   <= dec_psel;
             state    <= APB_SETUP;
           end else begin
             pwrite_q <= 1'b1;
             bresp_q  <= 2'b11;
             state    <= UNMAPPED_W;
           end
         end
       end
       UNMAPPED_W: begin
         state <= RESP;
       end
       UNMAPPED_R: begin
         state <= RESP;
       end
       APB_SETUP: begin
         state <= APB_ACCESS;
       end
       APB_ACCESS: begin
         if (pready[psel_q]) begin
           if (pwrite_q) begin
             bresp_q <= pslverr[psel_q] ? 2'b10 : 2'b00;
           end else begin
             rdata_q <= prdata[32*psel_q +: 32];
             rresp_q <= pslverr[psel_q] ? 2'b10 : 2'b00;
           end
           state <= RESP;
         end
       end
       RESP: begin
         if (pwrite_q) begin
           if (s_bready) begin
             aw_got_q <= 1'b0;
             w_got_q  <= 1'b0;
             psel_q   <= 3'b000;
             state    <= IDLE;
           end
         end else begin
           if (s_rready) begin
             psel_q <= 3'b000;
             state  <= IDLE;
           end
         end
       end
       default: state <= IDLE;
     endcase
   end
 end

 function automatic logic rd_map_comb(input logic [31:0] a);
   rd_map_comb = (a >= 32'h00001000 && a <= 32'h00001fff) ||
                 (a >= 32'h00008000 && a <= 32'h00009fff) ||
                 (a >= 32'h40000000 && a <= 32'h40000fff);
 endfunction

 function automatic logic [31:0] rd_local(input logic [31:0] a);
   if (a >= 32'h00001000 && a <= 32'h00001fff) rd_local = a - 32'h00001000;
   else if (a >= 32'h00008000 && a <= 32'h00009fff) rd_local = a - 32'h00008000;
   else rd_local = a - 32'h40000000;
 endfunction

 function automatic logic [2:0] rd_sel(input logic [31:0] a);
   if (a >= 32'h00001000 && a <= 32'h00001fff) rd_sel = 3'b001;
   else if (a >= 32'h00008000 && a <= 32'h00009fff) rd_sel = 3'b010;
   else rd_sel = 3'b100;
 endfunction

endmodule
