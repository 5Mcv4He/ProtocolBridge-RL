set target_library $env(CLASS_DB)
set link_library "* $target_library"
set_svf mapping.svf
set a [analyze -format sverilog bridge.sv]
puts "PB_ANALYZE=$a"
if {!$a} {quit}
elaborate bridge
current_design bridge
set l [link]
puts "PB_LINK=$l"
if {!$l} {quit}
source constraints.tcl
set d [check_design]
puts "PB_DESIGN=$d"
set c [compile -map_effort medium]
puts "PB_COMPILE=$c"
if {!$c} {quit}
puts "PB_LATCHES=[sizeof_collection [all_registers -level_sensitive]]"
report_area
report_timing -max_paths 1
write -format verilog -hierarchy -output mapped.v
write_sdc mapped.sdc
set_svf -off
puts "PB_DC_DONE=1"
quit
