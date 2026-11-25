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

  // Request half buffers
  logic aw_valid_q;
  logic [31:0] aw_addr_q;
  logic w_valid_q;
  logic [31:0] w_data_q;
  logic [3:0] w_strb_q;

  // Response buffers
  logic bvalid_q;
  logic [1:0] bresp_q;
  logic rvalid_q;
  logic [31:0] rdata_q;
  logic [1:0] rresp_q;

  // APB state
  logic apb_active;      // 1 from setup through access completion
  logic apb_access;      // 1 during access phase

  // Decoded request
  logic req_is_read;
  logic [31:0] req_addr;
  logic req_unmapped;
  logic [2:0] req_sel;
  logic [31:0] req_paddr;
  logic [31:0] req_wdata;
  logic [3:0] req_wstrb;

  wire mapped_do = 1'b1; // for clarity

  // Decode an address into one-hot sel / unmapped
  function automatic void decode(input logic [31:0] a, output logic [2:0] sel, output logic unmap);
    if (a >= 32'h0000_1000 && a <= 32'h0000_1fff) begin
      sel = 3'b001; unmap = 1'b0;
    end else if (a >= 32'h0000_8000 && a <= 32'h0000_9fff) begin
      sel = 3'b010; unmap = 1'b0;
    end else if (a >= 32'h4000_0000 && a <= 32'h4000_0fff) begin
      sel = 3'b100; unmap = 1'b0;
    end else begin
      sel = 3'b000; unmap = 1'b1;
    end
  endfunction

  logic [2:0] dec_sel;
  logic dec_unmap;

  // Determine the effectively accepted request combination
  // Read path
  logic ar_accept;
  assign ar_accept = s_arvalid && s_arready;
  logic aw_accept, w_accept;
  assign aw_accept = s_awvalid && s_awready;
  assign w_accept  = s_wvalid  && s_wready;

  // Both halves present (including those accepted this cycle)
  logic [31:0] cur_awaddr;
  logic cur_have_aw, cur_have_w;
  logic [31:0] cur_wdata;
  logic [3:0]  cur_wstrb;

  always_comb begin
    // combine stored and incoming on the fly
    if (aw_valid_q) begin
      cur_have_aw = 1'b1; cur_awaddr = aw_addr_q;
    end else if (s_awvalid && s_awready) begin
      cur_have_aw = 1'b1; cur_awaddr = s_awaddr;
    end else begin
      cur_have_aw = 1'b0; cur_awaddr = 32'h0;
    end
    if (w_valid_q) begin
      cur_have_w = 1'b1; cur_wdata = w_data_q; cur_wstrb = w_strb_q;
    end else if (s_wvalid && s_wready) begin
      cur_have_w = 1'b1; cur_wdata = s_wdata; cur_wstrb = s_wstrb;
    end else begin
      cur_have_w = 1'b0; cur_wdata = 32'h0; cur_wstrb = 4'h0;
    end
  end

  // Select request to execute
  logic start_read;
  logic start_write;
  logic [31:0] start_addr;

  always_comb begin
    start_read = 1'b0;
    start_write = 1'b0;
    start_addr = 32'h0;
    if (!apb_active && !bvalid_q && !rvalid_q) begin
      if (ar_accept) begin
        start_read = 1'b1;
        start_addr = s_araddr;
      end else if (!(s_arvalid && s_arready) && cur_have_aw && cur_have_w) begin
        // write both halves available
        start_write = 1'b1;
        start_addr = cur_awaddr;
      end
    end
  end

  // Ready signals: accept when idle enough
  assign s_awready = rst_n && !aw_valid_q && !apb_active && !bvalid_q && !rvalid_q && !(s_arvalid && s_arready && !s_arvalid);
  // simpler: awready high when no buffered aw, not busy
  // recompute below

  // We'll implement ready logic more carefully in sequential form via combinational override below.

  always_comb begin
    s_awready = 1'b0;
    s_wready  = 1'b0;
    s_arready = 1'b0;
    if (rst_n && !apb_active && !bvalid_q && !rvalid_q) begin
      // Accept AR if it can start immediately (no buffered write halves)
      if (s_arvalid && !aw_valid_q && !w_valid_q) begin
        s_arready = 1'b1;
      end
      // Accept AW when not buffered and not going to start a read this cycle
      if (s_awvalid && !aw_valid_q && !(s_arvalid && !aw_valid_q && !w_valid_q)) begin
        s_awready = 1'b1;
      end
      // Accept W when not buffered
      if (s_wvalid && !w_valid_q) begin
        s_wready = 1'b1;
      end
    end
  end

  // recompute start conditions without circular ready usage
  // Re-evaluate using buffered+incoming after ready combos.

  always_comb begin
    dec_sel   = 3'b000;
    dec_unmap = 1'b1;
    decode(start_addr, dec_sel, dec_unmap);
  end

  // APB outputs
  always_comb begin
    psel    = 3'b000;
    penable = 1'b0;
    pwrite  = 1'b0;
    paddr   = 32'h0;
    pwdata  = 32'h0;
    pstrb   = 4'h0;
    pprot   = 3'b000;
    if (apb_active) begin
      psel   = req_sel;
      paddr  = req_paddr;
      pwrite = ~req_is_read;
      pwdata = req_wdata;
      pstrb  = req_wstrb;
      penable = apb_access;
    end
  end

  // Response outputs
  assign s_bvalid = bvalid_q;
  assign s_bresp  = bresp_q;
  assign s_rvalid = rvalid_q;
  assign s_rdata  = rdata_q;
  assign s_rresp  = rresp_q;

  // Selected target completion
  logic sel_ready, sel_err;
  logic [31:0] sel_rdata;
  always_comb begin
    sel_ready = 1'b0;
    sel_err   = 1'b0;
    sel_rdata = 32'h0;
    case (req_sel)
      3'b001: begin sel_ready = pready[0]; sel_err = pslverr[0]; sel_rdata = prdata[31:0];   end
      3'b010: begin sel_ready = pready[1]; sel_err = pslverr[1]; sel_rdata = prdata[63:32];  end
      3'b100: begin sel_ready = pready[2]; sel_err = pslverr[2]; sel_rdata = prdata[95:64];  end
      default: begin sel_ready = 1'b0; sel_err = 1'b0; sel_rdata = 32'h0; end
    endcase
  end

  // Unmapped response delay counter
  logic [4:0] unmap_cnt;

  // Sequential
  always_ff @(posedge clk) begin
    if (!rst_n) begin
      aw_valid_q <= 1'b0;
      aw_addr_q  <= 32'h0;
      w_valid_q  <= 1'b0;
      w_data_q   <= 32'h0;
      w_strb_q   <= 4'h0;
      bvalid_q   <= 1'b0;
      bresp_q    <= 2'b00;
      rvalid_q   <= 1'b0;
      rdata_q    <= 32'h0;
      rresp_q    <= 2'b00;
      apb_active <= 1'b0;
      apb_access <= 1'b0;
      req_is_read<= 1'b0;
      req_addr   <= 32'h0;
      req_unmapped <= 1'b0;
      req_sel    <= 3'b000;
      req_paddr  <= 32'h0;
      req_wdata  <= 32'h0;
      req_wstrb  <= 4'h0;
      unmap_cnt  <= 5'd0;
    end else begin
      // 1) Capture accepted halves
      if (s_awvalid && s_awready) begin
        aw_valid_q <= 1'b1;
        aw_addr_q  <= s_awaddr;
      end
      if (s_wvalid && s_wready) begin
        w_valid_q <= 1'b1;
        w_data_q  <= s_wdata;
        w_strb_q  <= s_wstrb;
      end

      // 2) Start transactions: reads take priority when AR offered and nothing buffered
      if (!apb_active && !bvalid_q && !rvalid_q) begin
        if (s_arvalid && s_arready) begin
          req_is_read  <= 1'b1;
          req_addr     <= s_araddr;
          decode(s_araddr, req_sel, req_unmapped);
          req_paddr    <= (s_araddr >= 32'h4000_0000) ? (s_araddr - 32'h4000_0000) :
                          (s_araddr >= 32'h0000_8000) ? (s_araddr - 32'h0000_8000) :
                                                        (s_araddr - 32'h0000_1000);
          req_wdata    <= 32'h0;
          req_wstrb    <= 4'h0;
          if (req_unmapped) begin
            // will assert RVALID shortly; use counter
            unmap_cnt <= 5'd1;
          end else begin
            apb_active <= 1'b1;
            apb_access <= 1'b0;
          end
        end else if ((aw_valid_q || (s_awvalid && s_awready)) &&
                     (w_valid_q  || (s_wvalid  && s_wready))) begin
          // both write halves available: capture values
          begin
            logic [31:0] a;
            logic [31:0] d;
            logic [3:0]  st;
            a  = aw_valid_q ? aw_addr_q : s_awaddr;
            d  = w_valid_q  ? w_data_q  : s_wdata;
            st = w_valid_q  ? w_strb_q  : s_wstrb;
            req_is_read <= 1'b0;
            req_addr    <= a;
            decode(a, req_sel, req_unmapped);
            req_paddr   <= (a >= 32'h4000_0000) ? (a - 32'h4000_0000) :
                           (a >= 32'h0000_8000) ? (a - 32'h0000_8000) :
                                                 (a - 32'h0000_1000);
            req_wdata   <= d;
            req_wstrb   <= st;
            // clear buffered halves
            aw_valid_q <= 1'b0;
            w_valid_q  <= 1'b0;
            if (req_unmapped) begin
              unmap_cnt <= 5'd1;
            end else begin
              apb_active <= 1'b1;
              apb_access <= 1'b0;
            end
          end
        end
      end

      // 3) Unmapped counter -> response
      if (unmap_cnt != 5'd0) begin
        if (unmap_cnt == 5'd1) begin
          unmap_cnt <= 5'd0;
          if (req_is_read) begin
            rvalid_q <= 1'b1;
            rresp_q  <= 2'b11;
            rdata_q  <= 32'h0;
          end else begin
            bvalid_q <= 1'b1;
            bresp_q  <= 2'b11;
          end
        end else begin
          unmap_cnt <= unmap_cnt - 5'd1;
        end
      end

      // 4) APB progress
      if (apb_active) begin
        if (!apb_access) begin
          apb_access <= 1'b1;
        end else begin
          if (sel_ready) begin
            apb_active <= 1'b0;
            apb_access <= 1'b0;
            if (req_is_read) begin
              rvalid_q <= 1'b1;
              rdata_q  <= sel_rdata;
              rresp_q  <= sel_err ? 2'b10 : 2'b00;
            end else begin
              bvalid_q <= 1'b1;
              bresp_q  <= sel_err ? 2'b10 : 2'b00;
            end
          end
        end
      end

      // 5) Response handshakes
      if (bvalid_q && s_bready) begin
        bvalid_q <= 1'b0;
      end
      if (rvalid_q && s_rready) begin
        rvalid_q <= 1'b0;
      end
    end
  end

endmodule
