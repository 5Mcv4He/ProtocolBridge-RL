# Compare candidate RTL with an independent trusted behavioral reference.
# No SVF, library, assumptions, user constraints, or candidate Tcl are loaded.
set synopsys_auto_setup false
set reference_read [read_sverilog -r reference.sv]
puts "PB_REFERENCE_READ=$reference_read"
set reference_top [set_top r:/WORK/accumulator]
puts "PB_REFERENCE_TOP=$reference_top"
set candidate_read [read_sverilog -i candidate.sv]
puts "PB_CANDIDATE_READ=$candidate_read"
set candidate_top [set_top i:/WORK/accumulator]
puts "PB_CANDIDATE_TOP=$candidate_top"
match
set result [verify]
puts "PB_REFERENCE_EQ=$result"
report_black_boxes
report_failing_points
report_unverified_points
report_aborted_points
report_matched_points
report_unmatched_points
puts "PB_REFERENCE_DONE=1"
exit
