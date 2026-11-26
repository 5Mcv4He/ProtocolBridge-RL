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

 // executor states
 typedef enum logic [2:0] {IDLE, SETUP, ACCESS, RESP_W, RESP_R} st_t;
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

 // A response handshake in current cycle frees credits next cycle (conservative).

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
   // ---- queue acceptance (only when slot free; credits held until response) ----
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

   // ---- APB defaults ----
   psel <= 1'b0; penable <= 1'b0; pwrite <= 1'b0;

   case (state)
    IDLE: begin
     // Do not select on an edge where a response is being consumed.
     if (!(b_pending && s_bready) && !(r_pending && s_rready)) begin
      if (write_elig || read_elig) begin
       if (write_elig && read_elig) begin
        sel_write <= !pref_read;
        if (pref_read) begin
         cur_addr <= ar_addr;
         pref_read <= 1'b0;
        end else begin
         cur_addr <= aw_addr; cur_wdata <= w_data; cur_strb <= w_strb;
         pref_read <= 1'b1;
        end
       end else if (write_elig) begin
        sel_write <= 1'b1;
        cur_addr <= aw_addr; cur_wdata <= w_data; cur_strb <= w_strb;
        pref_read <= 1'b0;
       end else begin
        sel_write <= 1'b0;
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
      state <= sel_write ? RESP_W : RESP_R;
     end
    end
    RESP_W: begin
     if (!b_pending) begin
      b_pending <= 1'b1;
      b_resp_pend <= cur_resp;
     end else if (s_bready) begin
      b_pending <= 1'b0;
      aw_full <= 1'b0;
      w_full  <= 1'b0;
      state <= IDLE;
     end
    end
    RESP_R: begin
     if (!r_pending) begin
      r_pending <= 1'b1;
      r_resp_pend <= cur_resp;
      r_data_pend <= cur_rdata;
     end else if (s_rready) begin
      r_pending <= 1'b0;
      ar_full <= 1'b0;
      state <= IDLE;
     end
    end
    default: state <= IDLE;
   endcase
  end
 end
endmodule
