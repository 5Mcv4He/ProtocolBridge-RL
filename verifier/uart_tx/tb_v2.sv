`timescale 1ns/1ps
`include "svt_uart.uvm.pkg"
import uvm_pkg::*;
import svt_uvm_pkg::*;
import svt_uart_uvm_pkg::*;

module tb;
  bit clk=0;always #5 clk=~clk;
  bit rst_n=0,valid=0;bit [7:0] data=0;
  wire ready,tx;int parity_mode,byte_order,expected[$],observed=0,checks=0,busy_offers=0,accepts=0,adjacent=0,cycle=0,last_accept=-1;bit finished=0;
  uart_tx dut(clk,rst_n,valid,data,ready,tx);
  svt_uart_if vif(clk);
  svt_uart_bfm_wrapper #(.UV_DEVICE_TYPE(`UV_DTE)) receiver(vif);
  assign vif.rst=~rst_n;
  assign vif.sin=tx;
  // Receiver-only passive VIP: its unused transmit line is valid idle.
  assign vif.sout=1'b1;
  assign vif.cts=0;
  assign vif.dsr=0;

  always @(posedge clk) begin
    cycle++;
    if(rst_n && valid && !ready)busy_offers++;
    if(rst_n && valid && ready)begin
      if(last_accept>=0 && cycle-last_accept==(parity_mode?177:161))adjacent++;
      last_accept=cycle;accepts++;
    end
  end

  class rx_test extends uvm_test;
    `uvm_component_utils(rx_test)
    svt_uart_agent agent;
    svt_uart_agent_configuration cfg;
    uvm_analysis_imp#(svt_uart_transaction,rx_test) received;
    function new(string name="rx_test",uvm_component parent=null);
      super.new(name,parent);received=new("received",this);
    endfunction
    function void build_phase(uvm_phase phase);
      super.build_phase(phase);
      cfg=svt_uart_agent_configuration::type_id::create("cfg");
      cfg.is_active=0;cfg.baud_divisor=1;cfg.enable_fractional_brd=0;
      cfg.data_width=svt_uart_configuration::EIGHT_BIT;
      cfg.stop_bit=svt_uart_configuration::ONE_BIT;
      cfg.parity_type=parity_mode ? svt_uart_configuration::EVEN_PARITY : svt_uart_configuration::NO_PARITY;
      cfg.enable_rts_cts_handshake=0;cfg.enable_dtr_dsr_handshake=0;cfg.enable_tx_rx_handshake=0;
      cfg.set_uart_if(vif);
      uvm_config_db#(svt_uart_agent_configuration)::set(this,"agent","cfg",cfg);
      agent=svt_uart_agent::type_id::create("agent",this);
    endfunction
    function void connect_phase(uvm_phase phase);
      agent.monitor.rx_xact_observed_port.connect(received);
    endfunction
    function void write(svt_uart_transaction tr);
      foreach(tr.payload[i]) begin
        if (observed>=expected.size() || tr.payload[i]!==expected[observed])
          `uvm_error("PB_DATA","VIP decoded byte differs from accepted request")
        observed++;
      end
    endfunction
    task run_phase(uvm_phase phase);
      phase.raise_objection(this);wait(finished);repeat(100) @(posedge clk);
      if(observed!=expected.size() || observed!=256) `uvm_error("PB_COUNT","Missing or extra decoded frames")
      if(observed==256 && checks==(parity_mode?45056:40960))
        $display("PB_UART_COMPLETE frames=%0d cycle_checks=%0d",observed,checks);
      $display("PB_UART_EXPOSURE busy=%0d adjacent=%0d accepted=%0d",busy_offers,adjacent,accepts);
      phase.drop_objection(this);
    endtask
  endclass

  task fail(string reason);
    $display("PB_UART_FUNCTIONAL_FAIL %s",reason);$finish;
  endtask
  task send_byte(input int value);
    int cycles;bit bit_expected;
    cycles=(parity_mode?11:10)*16;
    @(negedge clk);if(ready!==1 || tx!==1) fail("idle");data=value;valid=1;
    expected.push_back(value);
    for(int j=0;j<cycles;j++) begin
      @(posedge clk);#1;
      if(j<16)bit_expected=0;
      else if(j<144)bit_expected=(value>>((j/16)-1))&1;
      else if(parity_mode && j<160)bit_expected=^(8'(value));
      else bit_expected=1;
      if(tx!==bit_expected)fail("serial_bit_or_duration");
      if(ready!==0)fail("busy_ready");
      checks++;
      @(negedge clk);valid=((j%7)==3 && j<cycles-2);data=~value;
    end
    @(posedge clk);#1;if(ready!==1 || tx!==1)fail("retire");
    // Next frame may be offered at the immediately following falling edge.
  endtask
  initial begin
    if(!$value$plusargs("parity=%d",parity_mode))parity_mode=0;
    if(!$value$plusargs("order=%d",byte_order))byte_order=0;
    run_test("rx_test");
  end
  initial begin
    repeat(12)@(negedge clk);rst_n=1;repeat(30)@(negedge clk);
    for(int i=0;i<256;i++)send_byte(byte_order==0 ? i : byte_order==1 ? 255-i : ((i*73+19)%256));
    finished=1;
  end
  initial begin #10000000;$display("PB_UART_TIMEOUT");$finish;end
endmodule
