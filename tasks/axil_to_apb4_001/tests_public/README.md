# Public active-VIP suite

From the repository root: `python3 -m environment.test WORKSPACE OUTPUT`.

32 transactions, deterministic seed 17, active AXI4-Lite master and APB4 slave
VIP. UVM compares intended and observed transactions. Final grading uses a
separate seed and 128 transactions. Both exercise AW/W order, zero/full/partial
strobes, repeated partial writes, APB waits/errors, response readiness and
between-transaction reset. Required pin coverage must be observed for reward 1.
Commercial VIP and VCS execute only on the configured licensed host.
