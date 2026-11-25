# Match the implementation tool interpretation using its own SVF guidance.
# This is synthesis consistency, not an independent proof of the Task Spec.
set synopsys_auto_setup true
set_svf mapping.svf
read_sverilog -r bridge.sv
set_top r:/WORK/bridge
read_db -i $env(CLASS_DB)
if {[file exists override.v]} {read_verilog -i override.v} else {read_verilog -i mapped.v}
set_top i:/WORK/bridge
match
set verified [verify]
puts "PB_EQUIVALENCE=$verified"
exit
