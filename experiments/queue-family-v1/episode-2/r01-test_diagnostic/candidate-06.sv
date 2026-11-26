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

 // AW queue
 logic [31:0] aw_addr [0:2];
 logic aw_valid [0:2];
 logic [1:0] aw_wp, aw_rp;
 logic [1:0] aw_cnt;

 // W queue
 logic [31:0] w_data [0:2];
 logic [3:0] w_strb [0:2];
 logic w_valid [0:2];
 logic [1:0] w_wp, w_rp;
 logic [1:0] w_cnt;

 // AR queue
 logic [31:0] ar_addr [0:2];
 logic ar_valid [0:2];
 logic [1:0] ar_wp, ar_rp;
 logic [1:0] ar_cnt;

 // Arbitration preference: 0=READ, 1=WRITE
 logic pref;

 // Executor states: IDLE, SETUP, ACCESS, RESP
 // RESP holds pending response until consumed; only one outstanding at a time.
 logic [1:0] state;
 logic sel_write;
 logic [31:0] cur_addr;
 logic [31:0] cur_wdata;
 logic [3:0] cur_strb;

 // Response registers
 logic bvalid_r, rvalid_r;
 logic [1:0] bresp_r, rresp_r;
 logic [31:0] rdata_r;

 // Ready signals
 assign s_awready = (aw_cnt != 2'd3);
 assign s_wready  = (w_cnt != 2'd3);
 assign s_arready = (ar_cnt != 2'd3);

 assign s_bvalid = bvalid_r;
 assign s_bresp  = bresp_r;
 assign s_rvalid = rvalid_r;
 assign s_rdata  = rdata_r;
 assign s_rresp  = rresp_r;

 // APB outputs
 assign psel = (state == 2'd1) || (state == 2'd2);
 assign penable = (state == 2'd2);
 assign pwrite = sel_write;
 assign paddr = cur_addr;
 assign pwdata = cur_wdata;
 assign pstrb = sel_write ? cur_strb : 4'd0;
 assign pprot = 3'b000;

 // Eligibility (based on pre-edge queue front entries)
 wire wr_eligible = aw_valid[aw_rp] && w_valid[w_rp];
 wire rd_eligible = ar_valid[ar_rp];

 integer i;

 always_ff @(posedge clk) begin
  if (!rst_n) begin
   aw_wp <= 0; aw_rp <= 0; aw_cnt <= 0;
   w_wp <= 0; w_rp <= 0; w_cnt <= 0;
   ar_wp <= 0; ar_rp <= 0; ar_cnt <= 0;
   pref <= 1'b0;
   state <= 2'd0;
   sel_write <= 0;
   cur_addr <= 0; cur_wdata <= 0; cur_strb <= 0;
   bvalid_r <= 0; rvalid_r <= 0;
   bresp_r <= 0; rresp_r <= 0; rdata_r <= 0;
   for (i=0;i<3;i=i+1) begin
    aw_valid[i] <= 0;
    w_valid[i] <= 0;
    ar_valid[i] <= 0;
   end
  end else begin
   // Default outputs for responses
   // Response consumption handled below

   // Accept AW
   if (s_awvalid && s_awready) begin
    aw_addr[aw_wp] <= s_awaddr;
    aw_valid[aw_wp] <= 1'b1;
    aw_wp <= (aw_wp == 2'd2) ? 2'd0 : (aw_wp + 2'd1);
   end

   // Accept W
   if (s_wvalid && s_wready) begin
    w_data[w_wp] <= s_wdata;
    w_strb[w_wp] <= s_wstrb;
    w_valid[w_wp] <= 1'b1;
    w_wp <= (w_wp == 2'd2) ? 2'd0 : (w_wp + 2'd1);
   end

   // Accept AR
   if (s_arvalid && s_arready) begin
    ar_addr[ar_wp] <= s_araddr;
    ar_valid[ar_wp] <= 1'b1;
    ar_wp <= (ar_wp == 2'd2) ? 2'd0 : (ar_wp + 2'd1);
   end

   // Update counts based on accepts and retirements, robust to simultaneous ops.
   // Compute deltas.
   begin
    logic [1:0] aw_inc, w_inc, ar_inc;
    logic aw_dec, w_dec, ar_dec;
    aw_inc = (s_awvalid && s_awready) ? 2'd1 : 2'd0;
    w_inc  = (s_wvalid  && s_wready ) ? 2'd1 : 2'd0;
    ar_inc = (s_arvalid && s_arready) ? 2'd1 : 2'd0;
    aw_dec = (state == 2'd3) && bvalid_r && s_bready;
    w_dec  = aw_dec;
    ar_dec = (state == 2'd3) && rvalid_r && s_rready;
    aw_cnt <= aw_cnt + aw_inc - (aw_dec ? 2'd1 : 2'd0);
    w_cnt  <= w_cnt  + w_inc  - (w_dec  ? 2'd1 : 2'd0);
    ar_cnt <= ar_cnt + ar_inc - (ar_dec ? 2'd1 : 2'd0);
   end

   // Response consumption (in RESP state)
   if (state == 2'd3) begin
    if (sel_write) begin
     // B response wins; consume when bready
     if (s_bready) begin
      bvalid_r <= 1'b0;
      aw_valid[aw_rp] <= 1'b0;
      w_valid[w_rp] <= 1'b0;
      aw_rp <= (aw_rp == 2'd2) ? 2'd0 : (aw_rp + 2'd1);
      w_rp <= (w_rp == 2'd2) ? 2'd0 : (w_rp + 2'd1);
      state <= 2'd0;
     end
    end else begin
     if (s_rready) begin
      rvalid_r <= 1'b0;
      ar_valid[ar_rp] <= 1'b0;
      ar_rp <= (ar_rp == 2'd2) ? 2'd0 : (ar_rp + 2'd1);
      state <= 2'd0;
     end
    end
   end

   // Executor FSM
   case (state)
    2'd0: begin // IDLE: can select
     if (wr_eligible || rd_eligible) begin
      if (wr_eligible && rd_eligible) begin
       if (pref == 1'b0) begin
        sel_write <= 1'b0;
        cur_addr <= ar_addr[ar_rp];
        state <= 2'd1;
        pref <= 1'b1;
       end else begin
        sel_write <= 1'b1;
        cur_addr <= aw_addr[aw_rp];
        cur_wdata <= w_data[w_rp];
        cur_strb <= w_strb[w_rp];
        state <= 2'd1;
        pref <= 1'b0;
       end
      end else if (rd_eligible) begin
       sel_write <= 1'b0;
       cur_addr <= ar_addr[ar_rp];
       state <= 2'd1;
       pref <= 1'b1;
      end else begin
       sel_write <= 1'b1;
       cur_addr <= aw_addr[aw_rp];
       cur_wdata <= w_data[w_rp];
       cur_strb <= w_strb[w_rp];
       state <= 2'd1;
       pref <= 1'b0;
      end
     end
    end
    2'd1: begin // SETUP -> ACCESS
     state <= 2'd2;
    end
    2'd2: begin // ACCESS wait
     if (pready) begin
      if (sel_write) begin
       bresp_r <= pslverr ? 2'b10 : 2'b00;
       bvalid_r <= 1'b1;
      end else begin
       rdata_r <= prdata;
       rresp_r <= pslverr ? 2'b10 : 2'b00;
       rvalid_r <= 1'b1;
      end
      state <= 2'd3;
     end
    end
    2'd3: begin // RESP: waiting for consumption; handled above
    end
    default: state <= 2'd0;
   endcase
  end
 end

endmodule
