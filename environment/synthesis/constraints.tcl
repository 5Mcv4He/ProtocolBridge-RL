# Frozen demonstration constraints, not a process/PPA contract for Tasks001-004.
create_clock -name clk -period 10 [get_ports clk]
set data_inputs [remove_from_collection [all_inputs] [get_ports clk]]
if {[sizeof_collection $data_inputs] > 0} {set_input_delay 0.1 -clock clk $data_inputs}
set_output_delay 0.1 -clock clk [all_outputs]
set_load 0.01 [all_outputs]
