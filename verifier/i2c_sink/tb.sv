`timescale 100ps/100ps
`include "svt_i2c.uvm.pkg"
module tb;
 import uvm_pkg::*;import svt_uvm_pkg::*;import svt_i2c_uvm_pkg::*;import svt_i2c_enum_pkg::*;
 bit clk=0;always #50 clk=~clk;
 bit vip_clk=0;always #5 vip_clk=~vip_clk;
 bit reset=0;initial begin #20;reset=1;#1000;reset=0;end
 svt_i2c_if bus(vip_clk);
 svt_i2c_master_wrapper master_bfm(bus);
 svt_i2c_slave_wrapper slave_bfm(bus);
 assign bus.RST=reset;
 wire low,valid;wire [15:0] data;
 i2c_sink dut(.clk(clk),.rst_n(!reset),.scl(bus.SCL),.sda(bus.SDA),.sda_drive_low(low),.item_valid(valid),.item_data(data));
 assign bus.SDA=low?1'b0:1'bz;
 int word_mode,nframes,total_bytes,total_items;
 int pin_planned[$],monitor_planned[$],frame_sizes[$],items[$];time deadlines[$];
 int delivered=0,observed=0,pin_bytes=0,starts=0,stops=0,acks=0,odd_frames=0;
 int bit_pos=0,decoded=0,frame_bytes=0,first=-1;bit in_frame=0,address_phase=1,prior_valid=0;
 time last_fall=0;
 task fail(string reason);$display("PB_I2C_FAIL %s",reason);$finish;endtask
 task infra(string reason);$display("PB_I2C_INFRA %s",reason);$finish;endtask
 // Independent event decoder: base-2 arithmetic over physical pins, no DUT state.
 always @(negedge bus.SDA)if(!reset && bus.SCL===1'b1)begin
  if(in_frame)fail("unexpected repeated start");
  in_frame=1;address_phase=1;bit_pos=0;decoded=0;frame_bytes=0;first=-1;starts++;
 end
 always @(posedge bus.SDA)if(!reset && bus.SCL===1'b1 && in_frame)begin
  if(bit_pos!=0 && bit_pos!=1)fail("STOP inside byte");
  if(frame_bytes%2)odd_frames++;
  in_frame=0;first=-1;stops++;
 end
 always @(negedge bus.SCL)last_fall=$time;
 always @(low)if(!reset && in_frame)begin
  if(low!==1'b0 && low!==1'b1)fail("unknown drive");
  if(bus.SCL!==1'b0)fail("drive changes while SCL high");
  if($time-last_fall<3000 || $time-last_fall>10000)fail("ack hold window");
 end
 always @(posedge bus.SCL)if(!reset && in_frame)begin
  if(bit_pos<8)begin
   if(bus.SDA!==1'b0 && bus.SDA!==1'b1)fail("unknown sampled data");
   decoded=2*decoded+(bus.SDA===1'b1);bit_pos++;
   if(bit_pos==8)begin
    if(address_phase)begin if(decoded!=164)fail("address bus corruption");end
    else begin
     int e;if(pin_planned.size()==0)fail("unplanned bus byte");
     e=pin_planned.pop_front();if(decoded!=e)fail("bus data corruption");
     frame_bytes++;pin_bytes++;
     if(!word_mode)begin items.push_back(decoded);deadlines.push_back($time+800);end
     else if(first<0)first=decoded;
     else begin items.push_back(256*first+decoded);deadlines.push_back($time+800);first=-1;end
    end
   end
  end else begin
   if(bus.SDA!==1'b0)fail("missing physical ACK");
   acks++;bit_pos=0;decoded=0;address_phase=0;
  end
 end
 always @(valid or data)if(!reset && valid===1'b1 && $time%100!=50)fail("asynchronous delivery");
 always @(posedge clk)begin
  #1;
  if(!reset)begin
   if(valid!==1'b0 && valid!==1'b1)fail("unknown valid");
   if(valid)begin
    int e;time d;
    if(prior_valid)fail("valid wider than one clock");
    if(items.size()==0)fail("early or extra delivery");
    e=items.pop_front();d=deadlines.pop_front();
    if(data!==e[15:0])fail("item identity or order");
    if($time-1>d)fail("late delivery");
    delivered++;
   end
   if(deadlines.size()>0 && $time-1>deadlines[0])fail("missing delivery");
   prior_valid=valid;
  end else begin
   prior_valid=0;
   if($time>200 && (low!==0 || valid!==0 || data!==0))fail("reset outputs");
  end
 end
 class stimulus extends uvm_sequence#(svt_i2c_master_transaction);
  `uvm_object_utils(stimulus)
  function new(string name="stimulus");super.new(name);endfunction
  task body();
   svt_i2c_master_transaction tr;int f,r,n,value;
   f=$fopen("stimulus.txt","r");r=$fscanf(f,"%d %d %d %d\n",word_mode,nframes,total_bytes,total_items);
   if(!f || r!=4 || nframes<1)infra("input header");
   for(int k=0;k<nframes;k++)begin
    r=$fscanf(f,"%d",n);if(r!=1 || n<1 || n>17)infra("input frame");
    tr=svt_i2c_master_transaction::type_id::create("tr");tr.reasonable_addr.constraint_mode(0);tr.reasonable_data.constraint_mode(0);start_item(tr);
    if(!tr.randomize() with {cmd==I2C_WRITE;addr==7'h52;addr_10bit==0;data.size()==n;sr_or_p_gen==0;send_start_byte==0;retry_if_nack==0;})`uvm_fatal("PB_INFRA","randomization")
    foreach(tr.data[i])begin
     r=$fscanf(f,"%d",value);if(r!=1 || value<0 || value>255)infra("input data");
     tr.data[i]=value;pin_planned.push_back(value);monitor_planned.push_back(value);
    end
    frame_sizes.push_back(n);finish_item(tr);
   end
   $fclose(f);
  endtask
 endclass
 class collector extends uvm_subscriber#(svt_i2c_master_transaction);
  `uvm_component_utils(collector)
  function new(string name,uvm_component parent);super.new(name,parent);endfunction
  function void write(svt_i2c_master_transaction tr);
   int n,e;observed++;
   if(frame_sizes.size()==0)begin `uvm_error("PB_SEMANTIC","unexpected transaction") return;end
   n=frame_sizes.pop_front();
   if(tr.cmd!=I2C_WRITE || tr.addr!=7'h52 || tr.data.size()!=n || tr.ack_detected.size()!=n+1)`uvm_error("PB_SEMANTIC","transaction metadata")
   foreach(tr.data[i])begin
    if(monitor_planned.size()==0)`uvm_error("PB_SEMANTIC","extra data")
    else begin e=monitor_planned.pop_front();if(tr.data[i]!=e)`uvm_error("PB_SEMANTIC","monitor data") end
   end
   foreach(tr.ack_detected[i])if(tr.ack_detected[i]!=1)`uvm_error("PB_SEMANTIC","monitor ACK")
  endfunction
 endclass
 class pb_test extends uvm_test;
  `uvm_component_utils(pb_test)
  svt_i2c_system_env env;svt_i2c_system_configuration cfg;collector monitor;
  function new(string name,uvm_component parent);super.new(name,parent);endfunction
  function void build_phase(uvm_phase phase);
   super.build_phase(phase);cfg=new("cfg");cfg.num_masters=1;cfg.num_slaves=1;cfg.create_sub_cfgs(1,1);
   cfg.master_cfg[0].is_active=1;cfg.slave_cfg[0].is_active=0;
   cfg.set_bus_speed(STANDARD_MODE);cfg.slave_cfg[0].slave_address=7'h52;cfg.slave_cfg[0].enable_10bit_addr=0;cfg.slave_cfg[0].slave_type=`SVT_I2C_GENERIC;
   cfg.set_if(bus);uvm_config_db#(svt_i2c_system_configuration)::set(this,"env","cfg",cfg);
   env=svt_i2c_system_env::type_id::create("env",this);monitor=collector::type_id::create("monitor",this);
  endfunction
  function void connect_phase(uvm_phase phase);super.connect_phase(phase);env.master[0].monitor.xact_observed_port.connect(monitor.analysis_export);endfunction
  task main_phase(uvm_phase phase);
   stimulus seq;phase.raise_objection(this);#3000;seq=stimulus::type_id::create("seq");seq.start(env.master[0].sequencer);#100000;
   if(delivered!=total_items || observed!=nframes || starts!=nframes || stops!=nframes || pin_bytes!=total_bytes || acks!=total_bytes+nframes || items.size()!=0 || pin_planned.size()!=0 || monitor_planned.size()!=0 || frame_sizes.size()!=0)fail("incomplete activity");
   else begin
    @(negedge clk);reset=1;repeat(5)@(posedge clk);@(negedge clk);reset=0;#1000;
    $display("PB_I2C_COMPLETE frames=%0d bytes=%0d items=%0d acks=%0d odd=%0d",observed,pin_bytes,delivered,acks,odd_frames);
   end
   phase.drop_objection(this);
  endtask
 endclass
 initial begin
 if($bits(dut.clk)!=1 || $bits(dut.rst_n)!=1 || $bits(dut.scl)!=1 || $bits(dut.sda)!=1 || $bits(dut.sda_drive_low)!=1 || $bits(dut.item_valid)!=1 || $bits(dut.item_data)!=16)begin $display("PB_I2C_INVALID_INTERFACE");$finish;end
 run_test("pb_test");end
 initial begin #200000000;infra("simulation watchdog");end
endmodule
