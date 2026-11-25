# Use implementation-compatible RTL interpretation, then prove directly.
# SVF is retained as evidence but is not loaded in this bounded small-design flow.
# This is synthesis consistency, not an independent proof of the Task Spec.
set synopsys_auto_setup true
read_sverilog -r bridge.sv
set_top r:/WORK/bridge
read_db -i $env(CLASS_DB)
if {[file exists override.v]} {read_verilog -i override.v} else {read_verilog -i mapped.v}
set_top i:/WORK/bridge
match
set verified [verify]
puts "PB_EQUIVALENCE=$verified"
exit
