module bridge(
 input logic clk,rst_n,
 input logic [31:0] s_awaddr, input logic s_awvalid, output logic s_awready,
 input logic [31:0] s_wdata, input logic [3:0] s_wstrb, input logic s_wvalid, output logic s_wready,
 output logic [1:0] s_bresp, output logic s_bvalid, input logic s_bready,
 input logic [31:0] s_araddr, input logic s_arvalid, output logic s_arready,
 output logic [31:0] s_rdata, output logic [1:0] s_rresp, output logic s_rvalid, input logic s_rready,
 output logic [31:0] paddr,pwdata, output logic [3:0] pstrb, output logic [2:0] pprot,
 output logic psel,penable,pwrite, input logic [31:0] prdata, input logic pready,pslverr
);

 // AW queue (capacity 2)
 logic [31:0] aw_addr [0:1];
 logic [1:0] aw_count; // number of unretired AW
 logic aw_head;         // index of oldest AW

 // W queue (capacity 2)
 logic [31:0] w_data [0:1];
 logic [3:0]  w_strb [0:1];
 logic [1:0] w_count;
 logic w_head;

 // AR queue (capacity 2)
 logic [31:0] ar_addr [0:1];
 logic [1:0] ar_count;
 logic ar_head;

 // APB executor state
 // state encoding
 localparam IDLE    = 2'd0;
 localparam SETUP   = 2'd1;
 localparam ACCESS  = 2'd2;
 localparam RESP    = 2'd3;

 logic [1:0] state;
 logic is_write;            // current transaction is write
 logic [31:0] cur_addr;
 logic [31:0] cur_wdata;
 logic [3:0]  cur_wstrb;
 logic [1:0]  cur_resp;     // captured response
 logic [31:0] cur_rdata;    // captured read data

 // registered round-robin preference: 1 = READ, 0 = WRITE
 logic pref_read;

 // ----------------------------------------------------------------
 // AXI acceptance (combinational ready)
 // AW queue tracks independent AW credits; retire on B consumption.
 // To keep AW/W pairing with independent credit counters, we track
 // separate AW and W queues, retiring one entry from each when B is
 // consumed. Since counts are independently bounded by 2, and each B
 // consumes one AW and one W, they stay consistent for paired writes;
 // we additionally gate eligibility on both counts > 0.

 assign s_awready = (aw_count < 2'd2);
 assign s_wready  = (w_count  < 2'd2);
 assign s_arready = (ar_count < 2'd2);

 // ----------------------------------------------------------------
 // APB outputs
 always @(*) begin
   psel   = (state == SETUP) || (state == ACCESS);
   penable= (state == ACCESS);
   pwrite = is_write;
   paddr  = cur_addr;
   pwdata = cur_wdata;
   pstrb  = is_write ? cur_wstrb : 4'b0000;
   pprot  = 3'b000;
 end

 // Response outputs
 assign s_bvalid = (state == RESP) && is_write;
 assign s_bresp  = cur_resp;
 assign s_rvalid = (state == RESP) && !is_write;
 assign s_rdata  = cur_rdata;
 assign s_rresp  = cur_resp;

 // ----------------------------------------------------------------
 // Sequential logic
 integer i;

 always @(posedge clk) begin
   if (!rst_n) begin
     aw_count <= 2'd0;
     w_count  <= 2'd0;
     ar_count <= 2'd0;
     aw_head  <= 1'b0;
     w_head   <= 1'b0;
     ar_head  <= 1'b0;
     for (i = 0; i < 2; i = i + 1) begin
       aw_addr[i] <= 32'd0;
       w_data[i]  <= 32'd0;
       w_strb[i]  <= 4'd0;
       ar_addr[i] <= 32'd0;
     end
     state    <= IDLE;
     is_write <= 1'b0;
     cur_addr <= 32'd0;
     cur_wdata<= 32'd0;
     cur_wstrb<= 4'd0;
     cur_resp <= 2'd0;
     cur_rdata<= 32'd0;
     pref_read<= 1'b1;
   end else begin
     // ---- accept AW ----
     if (s_awvalid && s_awready) begin
       // write into slot at index (aw_head + aw_count) mod 2
       if (aw_count == 2'd0)
         aw_addr[aw_head] <= s_awaddr;
       else
         aw_addr[~aw_head] <= s_awaddr;
       aw_count <= aw_count + 2'd1;
     end

     // ---- accept W ----
     if (s_wvalid && s_wready) begin
       if (w_count == 2'd0) begin
         w_data[w_head] <= s_wdata;
         w_strb[w_head] <= s_wstrb;
       end else begin
         w_data[~w_head] <= s_wdata;
         w_strb[~w_head] <= s_wstrb;
       end
       w_count <= w_count + 2'd1;
     end

     // ---- accept AR ----
     if (s_arvalid && s_arready) begin
       if (ar_count == 2'd0)
         ar_addr[ar_head] <= s_araddr;
       else
         ar_addr[~ar_head] <= s_araddr;
       ar_count <= ar_count + 2'd1;
     end

     // ---- executor ----
     case (state)
       IDLE: begin
         // eligibility based on pre-edge buffered requests
         // (they were registered on prior edges; new accepts this edge
         //  must not be visible). Counts read here are pre-edge values
         //  since nonblocking assignments haven't updated them.
         if ((w_count > 2'd0) && (aw_count > 2'd0) && (ar_count > 2'd0)) begin
           if (pref_read) begin
             // select read
             is_write  <= 1'b0;
             cur_addr  <= ar_addr[ar_head];
             cur_wdata <= 32'd0;
             cur_wstrb <= 4'd0;
             state     <= SETUP;
             pref_read <= 1'b0;
             ar_count  <= ar_count - 2'd1;
             ar_head   <= ~ar_head;
           end else begin
             // select write
             is_write  <= 1'b1;
             cur_addr  <= aw_addr[aw_head];
             cur_wdata <= w_data[w_head];
             cur_wstrb <= w_strb[w_head];
             state     <= SETUP;
             pref_read <= 1'b1;
             // AW and W retired on B consumption, not here
           end
         end else if ((w_count > 2'd0) && (aw_count > 2'd0)) begin
           // only write eligible
           is_write  <= 1'b1;
           cur_addr  <= aw_addr[aw_head];
           cur_wdata <= w_data[w_head];
           cur_wstrb <= w_strb[w_head];
           state     <= SETUP;
           pref_read <= 1'b1;
         end else if (ar_count > 2'd0) begin
           // only read eligible
           is_write  <= 1'b0;
           cur_addr  <= ar_addr[ar_head];
           cur_wdata <= 32'd0;
           cur_wstrb <= 4'd0;
           state     <= SETUP;
           pref_read <= 1'b0;
           ar_count  <= ar_count - 2'd1;
           ar_head   <= ~ar_head;
         end
       end
       SETUP: begin
         state <= ACCESS;
       end
       ACCESS: begin
         if (pready) begin
           cur_resp <= pslverr ? 2'b10 : 2'b00;
           cur_rdata<= prdata;
           state    <= RESP;
         end
       end
       RESP: begin
         if (is_write) begin
           if (s_bready) begin
             state <= IDLE;
             // retire AW and W
             aw_count <= aw_count - 2'd1;
             aw_head  <= ~aw_head;
             w_count  <= w_count - 2'd1;
             w_head   <= ~w_head;
           end
         end else begin
           if (s_rready) begin
             state <= IDLE;
           end
         end
       end
       default: state <= IDLE;
     endcase
   end
 end

endmodule
