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

 // AW queue (depth 1)
 logic aw_full;
 logic [31:0] aw_addr;
 // W queue (depth 1)
 logic w_full;
 logic [31:0] w_data;
 logic [3:0] w_strb;
 // AR queue (depth 1)
 logic ar_full;
 logic [31:0] ar_addr;

 // pending write pairing consumed at selection time: when a write selected, both halves retired.

 // executor state
 typedef enum logic [1:0] {IDLE, SETUP, ACCESS, RESP} st_t;
 st_t state;

 logic sel_write;      // direction of current transaction
 logic [31:0] cur_addr;
 logic [31:0] cur_wdata;
 logic [3:0] cur_strb;
 logic [1:0] cur_resp;
 logic [31:0] cur_rdata;

 logic pref_read;      // 1 = prefer read

 // B/R response pending registers
 logic b_pending;
 logic [1:0] b_resp_pend;
 logic r_pending;
 logic [1:0] r_resp_pend;
 logic [31:0] r_data_pend;

 // eligibility (buffered before edge)
 wire write_elig = aw_full && w_full;
 wire read_elig  = ar_full;

 // accept readiness: accept when not full, BUT if a response for that direction is
 // being consumed this edge, the slot frees; conservative: only free next cycle.
 // Same-edge reuse allowed by spec, but conservative is legal. However selection
 // retires AW/W at selection (write) and AR at selection (read) - actually retire
 // AW/W only on B handshake, AR only on R handshake. So credit held until response.
 // But selection copies payload; AW/W/AR queues remain full until response consumed.

 assign s_awready = !aw_full;
 assign s_wready  = !w_full;
 assign s_arready = !ar_full;

 assign s_bvalid = b_pending;
 assign s_bresp  = b_resp_pend;
 assign s_rvalid = r_pending;
 assign s_rresp  = r_resp_pend;
 assign s_rdata  = r_data_pend;

 assign pprot = 3'b000;

 always_ff @(posedge clk) begin
  if (!rst_n) begin
   aw_full <= 1'b0; aw_addr <= 0;
   w_full <= 1'b0; w_data <= 0; w_strb <= 0;
   ar_full <= 1'b0; ar_addr <= 0;
   state <= IDLE;
   sel_write <= 1'b0; cur_addr <= 0; cur_wdata <= 0; cur_strb <= 0;
   cur_resp <= 0; cur_rdata <= 0;
   pref_read <= 1'b1;
   b_pending <= 1'b0; b_resp_pend <= 0;
   r_pending <= 1'b0; r_resp_pend <= 0; r_data_pend <= 0;
   psel <= 1'b0; penable <= 1'b0; pwrite <= 1'b0;
   paddr <= 0; pwdata <= 0; pstrb <= 0;
  end else begin
   // defaults for APB outputs driven by state below
   // ---- queue acceptance ----
   if (s_awvalid && s_awready) begin
    aw_full <= 1'b1; aw_addr <= s_awaddr;
   end
   if (s_wvalid && s_wready) begin
    w_full <= 1'b1; w_data <= s_wdata; w_strb <= s_wstrb;
   end
   if (s_arvalid && s_arready) begin
    ar_full <= 1'b1; ar_addr <= s_araddr;
   end

   // ---- response handshakes free credits ----
   if (s_bvalid && s_bready) begin
    b_pending <= 1'b0;
    aw_full <= 1'b0;
    w_full  <= 1'b0;
   end
   if (s_rvalid && s_rready) begin
    r_pending <= 1'b0;
    ar_full <= 1'b0;
   end

   // ---- executor ----
   case (state)
    IDLE: begin
     psel <= 1'b0; penable <= 1'b0; pwrite <= 1'b0;
     // Note: a response consumed this edge must make executor idle NEXT edge.
     // We handle that by not selecting if a handshake is happening this edge.
     if (!(b_pending && s_bready) && !(r_pending && s_rready)) begin
      if (write_elig || read_elig) begin
       if (write_elig && read_elig) sel_write <= !pref_read;
       else sel_write <= write_elig;
       if (write_elig && read_elig) begin
        // choose per preference
        if (pref_read) begin
         // read chosen
         cur_addr <= ar_addr;
         pref_read <= 1'b0;
        end else begin
         cur_addr <= aw_addr;
         cur_wdata <= w_data; cur_strb <= w_strb;
         pref_read <= 1'b1;
        end
       end else if (write_elig) begin
        cur_addr <= aw_addr;
        cur_wdata <= w_data; cur_strb <= w_strb;
        pref_read <= 1'b0;
       end else begin
        cur_addr <= ar_addr;
        pref_read <= 1'b0;
       end
       state <= SETUP;
      end
     end
    end
    SETUP: begin
     psel <= 1'b1; penable <= 1'b0; pwrite <= sel_write;
     paddr <= cur_addr;
     if (sel_write) begin pwdata <= cur_wdata; pstrb <= cur_strb; end
     else begin pwdata <= 32'b0; pstrb <= 4'b0; end
     state <= ACCESS;
    end
    ACCESS: begin
     psel <= 1'b1; penable <= 1'b1; pwrite <= sel_write;
     paddr <= cur_addr;
     if (sel_write) begin pwdata <= cur_wdata; pstrb <= cur_strb; end
     else begin pwdata <= 32'b0; pstrb <= 4'b0; end
     if (pready) begin
      psel <= 1'b0; penable <= 1'b0;
      cur_resp <= pslverr ? 2'b10 : 2'b00;
      cur_rdata <= prdata;
      state <= RESP;
     end
    end
    RESP: begin
     psel <= 1'b0; penable <= 1'b0; pwrite <= 1'b0;
     if (sel_write) begin
      b_pending <= 1'b1;
      b_resp_pend <= cur_resp;
      // if B consumed in same edge RESP entered? no, one cycle later at least.
      if (s_bready && b_pending) begin
       // consumed
       b_pending <= 1'b0;
       aw_full <= 1'b0; w_full <= 1'b0;
       state <= IDLE;
      end else begin
       state <= RESP;
      end
      // handling when b not pending yet: first cycle in RESP sets pending
     end else begin
      r_pending <= 1'b1;
      r_resp_pend <= cur_resp;
      r_data_pend <= cur_rdata;
      if (s_rready && r_pending) begin
       r_pending <= 1'b0;
       ar_full <= 1'b0;
       state <= IDLE;
      end else begin
       state <= RESP;
      end
     end
    end
    default: state <= IDLE;
   endcase
  end
 end
endmodule
