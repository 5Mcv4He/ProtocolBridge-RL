`timescale 1ns/1ps
`define SVT_MIPI_RFFE_MAX_NUM_OF_MASTERS 1
`define SVT_MIPI_RFFE_MAX_NUM_OF_SLAVES 1
`include "svt_mipi_rffe.uvm.pkg"
module top;
 import uvm_pkg::*;import svt_uvm_pkg::*;import svt_mipi_rffe_uvm_pkg::*;
 svt_mipi_rffe_if master_if();svt_mipi_rffe_if slave_if();svt_mipi_rffe_if mon_if();
 tri sclk,sdata;wire vio=1'b1;bit clk=0,rst_n=0;wire d,oe;always #1 clk=~clk;
 tran(master_if.sclk[0],sclk);tran(master_if.sdata[0],sdata);tran(master_if.vio[0],vio);
 tran(slave_if.sclk[0],sclk);tran(slave_if.sdata[0],sdata);tran(slave_if.vio[0],vio);
 tran(mon_if.sclk[0],sclk);tran(mon_if.sdata[0],sdata);tran(mon_if.vio[0],vio);
 wire si=(sclk===1'b1),di=(sdata===1'b1);
 assign sdata=oe?d:1'bz;rffe_register dut(clk,rst_n,si,di,d,oe);
 integer total,kind[2048],addr[2048],value[2048];integer pin_frames=0,tx_frames=0,rx_frames=0,expected_reads=0,expected_frames=0,expected_resets=0,pin_resets=0;
 bit loaded=0;
 task fail(string why);$display("PB_RFFE_MISMATCH %s",why);$finish;endtask
 initial begin
  integer f,r;f=$fopen("commands.txt","r");r=$fscanf(f,"%d\n",total);
  if(!f||r!=1||total<1||total>2048)begin $display("PB_RFFE_INFRA input");$finish;end
  for(integer i=0;i<total;i=i+1)begin
   r=$fscanf(f,"%d %d %d\n",kind[i],addr[i],value[i]);
   if(r!=3||kind[i]<0||kind[i]>2||addr[i]<0||addr[i]>15||value[i]<0||value[i]>255)begin $display("PB_RFFE_INFRA row");$finish;end
   if(kind[i]==0)expected_reads++;if(kind[i]==2)expected_resets++;else expected_frames++;
  end
  loaded=1;#100;rst_n=1;
 end
 task collect_frame(input integer width,output integer data);
  logic sampled;data=0;
  for(integer b=0;b<width;b=b+1)begin
   @(negedge sclk);#0.001;sampled=sdata;
   if(sampled!==0&&sampled!==1)fail("nonbinary frame bit");
   data=data*2+sampled;
  end
 endtask
 task park();
  @(posedge sclk);#0.002;if(sdata!==0)fail("park must drive zero");
  @(negedge sclk);#13;if(sdata!==1'bz)fail("park must release");
 endtask
 initial begin
  integer bits,header,payload;
  wait(loaded);
  for(integer row=0;row<total;row=row+1)begin
   if(kind[row]==2)begin @(negedge rst_n);@(posedge rst_n);pin_resets++;end
   else begin
   do @(posedge sdata);while(sdata!==1'b1||sclk!==1'b0);
   @(negedge sdata);if(sclk!==0||sdata!==0)fail("SSC shape");
   collect_frame(13,bits);header=bits/2;
   if(header!=(256+(kind[row]?64:96)+addr[row]))fail("command identity or address");
   if((^bits[12:0])!==1'b1)fail("command parity");
   if(!kind[row])park();
   collect_frame(9,payload);
   if((payload/2)!=value[row])fail("pin data mismatch");
   if((^payload[8:0])!==1'b1)fail("data parity");
   park();pin_frames++;
   end
  end
 end
 class observer extends uvm_subscriber#(svt_mipi_rffe_transaction);
  `uvm_component_utils(observer)
  integer read_index=0,tx_index=0;
  function new(string n="observer",uvm_component p=null);super.new(n,p);endfunction
  function void write(svt_mipi_rffe_transaction t);
   bit is_write;
   is_write=(t.command_type==svt_mipi_rffe_types::REGISTER_WRITE);
   if(is_write || (t.command_type==svt_mipi_rffe_types::REGISTER_READ && t.data_frame.size()==0))begin
    while(tx_index<total && kind[tx_index]==2)tx_index++;
    if(tx_index>=total)begin $display("PB_RFFE_MISMATCH extra VIP request");$finish;end
    if(t.device_id!=1||t.address_frame!=addr[tx_index]||is_write!=kind[tx_index])begin $display("PB_RFFE_MISMATCH VIP request identity");$finish;end
    if(is_write && (t.data_frame.size()!=1||t.data_frame[0]!=value[tx_index]))begin $display("PB_RFFE_MISMATCH VIP write data");$finish;end
    tx_frames++;tx_index++;
   end else if(t.command_type==svt_mipi_rffe_types::REGISTER_READ && t.data_frame.size()==1)begin
    while(read_index<total && kind[read_index])read_index++;
    if(read_index>=total||t.device_id!=1||t.address_frame!=addr[read_index]||t.data_frame[0]!=value[read_index])begin $display("PB_RFFE_MISMATCH VIP readback");$finish;end
    rx_frames++;read_index++;
   end else begin $display("PB_RFFE_MISMATCH unexpected VIP transaction");$finish;end
  endfunction
 endclass
 class cfg_t extends svt_mipi_rffe_system_configuration;
  `uvm_object_utils(cfg_t)
  constraint finite_bus {num_masters==1;num_slaves==1;num_dut_masters==0;num_dut_slaves==0;system_sclk_freq_Hz==1000000;system_enable_sread==0;system_enable_hsdr==0;system_enable_half_subrate==0;foreach(master_cfg[i]){master_cfg[i].is_master_vio_capable==0;master_cfg[i].rffe_version==svt_mipi_rffe_types::RFFE_VERSION_2_0;master_cfg[i].duty_cycle==50;} foreach(slave_cfg[i]){slave_cfg[i].rffe_version==svt_mipi_rffe_types::RFFE_VERSION_2_0;slave_cfg[i].duty_cycle==0;}}
  function new(string n="cfg_t");super.new(n);endfunction
 endclass
 class pb_rffe_test extends uvm_test;
  `uvm_component_utils(pb_rffe_test)
  svt_mipi_rffe_system_env env;cfg_t cfg;observer obs;
  function new(string n="pb_rffe_test",uvm_component p=null);super.new(n,p);endfunction
  function void build_phase(uvm_phase p);
   super.build_phase(p);cfg=cfg_t::type_id::create("cfg");if(!cfg.randomize())`uvm_fatal("CFG","randomize")
   // Device-specific register semantics and external reset belong to the
   // independent oracle. Mask only VIP memory-value prediction, not protocol checks.
   for(integer j=0;j<16;j=j+1)begin cfg.master_cfg[0].mask_data_integrity[j]=8'hff;cfg.slave_cfg[0].mask_data_integrity[j]=8'hff;end
   cfg.slave_cfg[0].is_active=0;cfg.slave_cfg[0].enable_monitor=1;
   uvm_config_db#(svt_mipi_rffe_system_configuration)::set(this,"env","cfg",cfg);
   env=svt_mipi_rffe_system_env::type_id::create("env",this);obs=observer::type_id::create("obs",this);
  endfunction
  function void connect_phase(uvm_phase p);
   super.connect_phase(p);env.master[0].master_mon.rx_xact_observed_port.connect(obs.analysis_export);env.master[0].master_mon.tx_xact_observed_port.connect(obs.analysis_export);
  endfunction
  task run_phase(uvm_phase p);
   svt_mipi_rffe_register_write_sequence w;svt_mipi_rffe_register_read_sequence r;
   p.raise_objection(this);wait(loaded);#10000;
   for(integer i=0;i<total;i=i+1)begin
    if(kind[i]==2)begin
     rst_n=0;#100;if(oe!==0)fail("reset must release bus");rst_n=1;#2000;
    end else if(kind[i])begin
     w=svt_mipi_rffe_register_write_sequence::type_id::create("w");w.set_sequencer(env.sequencer);
     if(!w.randomize() with {device_id==1;address_frame==addr[i];data_frame.size()==1;data_frame[0]==value[i];bus_id==svt_mipi_rffe_types::RFFE_BUS_0;})`uvm_fatal("W","randomize")
     w.start(env.sequencer);
    end else begin
     r=svt_mipi_rffe_register_read_sequence::type_id::create("r");r.set_sequencer(env.sequencer);
     if(!r.randomize() with {device_id==1;address_frame==addr[i];bus_id==svt_mipi_rffe_types::RFFE_BUS_0;})`uvm_fatal("R","randomize")
     r.start(env.sequencer);
    end
    #2000;
   end
   #5000;
   if(pin_frames!=expected_frames||tx_frames!=expected_frames||rx_frames!=expected_reads||pin_resets!=expected_resets)begin $display("PB_RFFE_INFRA incomplete pin=%0d tx=%0d rx=%0d",pin_frames,tx_frames,rx_frames);$finish;end
   $display("PB_RFFE_COMPLETE frames=%0d reads=%0d resets=%0d",pin_frames,rx_frames,pin_resets);p.drop_objection(this);
  endtask
 endclass
 initial begin
  uvm_config_db#(virtual svt_mipi_rffe_if)::set(null,"uvm_test_top.env","master_if[0]",master_if);
  uvm_config_db#(virtual svt_mipi_rffe_if)::set(null,"uvm_test_top.env","slave_if[0]",slave_if);
  uvm_config_db#(virtual svt_mipi_rffe_if)::set(null,"uvm_test_top.env","system_mon_if",mon_if);run_test("pb_rffe_test");
 end
 initial begin #20000000;$display("PB_RFFE_INFRA watchdog");$finish;end
endmodule
