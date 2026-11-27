# Fixed structural check, not a PPA objective. No candidate constraints loaded.
set target_library $env(CLASS_DB)
set link_library "* $target_library"
set a [analyze -format sverilog candidate.sv]
puts "PB_ANALYZE=$a"
if {!$a} {quit}
set e [elaborate bitfold]
puts "PB_ELABORATE=$e"
if {$e == "0" || $e == ""} {quit}
current_design bitfold
set l [link]
puts "PB_LINK=$l"
if {!$l} {quit}
set d [check_design]
puts "PB_DESIGN=$d"
if {!$d} {quit}
create_clock -name virtual -period 10
set_input_delay 0.1 -clock virtual [all_inputs]
set_output_delay 0.1 -clock virtual [all_outputs]
set c [compile -map_effort medium]
puts "PB_COMPILE=$c"
if {!$c} {quit}
puts "PB_REGISTERS=[sizeof_collection [all_registers]]"
puts "PB_UNMAPPED=[sizeof_collection [get_cells -hierarchical -filter is_unmapped]]"
puts "PB_CELLS=[sizeof_collection [get_cells -hierarchical *]]"
set w [write -format verilog -hierarchy -output mapped.v]
puts "PB_WRITE=$w"
puts "PB_DONE=1"
quit
