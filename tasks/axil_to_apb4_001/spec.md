# AXI4-Lite to APB4, task 001 v2
Implement module `bridge` with the exact ports in workspace/bridge.sv.
All signals use one rising-edge clock clk. rst_n is active-low synchronous reset;
reset clears buffered requests and responses and drives PSEL/PENABLE/BVALID/RVALID low.
The master must wait until the preceding B or R handshake before beginning another
transaction. No overlapping read/write transactions. Within a write, AW and W
are independent and may arrive in either order or together, with arbitrary gaps.
VALID and payload remain stable until READY. READY must not depend on VALID for
forward progress. Buffer each accepted half exactly once.
32-bit byte addresses, aligned to 4 bytes, are passed unchanged; all address bits
are significant. One APB target, no address decoding. 32-bit data. AWPROT/ARPROT
are omitted; PPROT is fixed 000. No bursts, IDs, exclusives or clock crossing.
Each request produces exactly one APB transfer: one setup cycle (PSEL=1,
PENABLE=0), then access (PSEL=PENABLE=1) until PREADY=1. Address, direction,
write data, strobe and protection stay stable throughout setup/access/wait.
Writes map WDATA and all four WSTRB bits unchanged, including zero strobe.
Reads drive PWRITE=0, PSTRB=0; PWDATA is irrelevant for reads.
Sample PRDATA and PSLVERR only on APB completion. AXI response is OKAY (00)
when PSLVERR=0 and SLVERR (10) otherwise; read RDATA equals PRDATA even on error.
BVALID/RVALID may not precede APB completion, must assert within 16 cycles of it,
and remain asserted with stable payload until BREADY/RREADY. No new APB request
while response is stalled. Once both AW/W (or AR) are accepted, begin setup
within 16 cycles. Once idle, accept each offered channel within 16 cycles.
Reset during an in-flight transaction aborts it; the requester and target also
reset and discard that transaction. This MVP tests initial and between-transaction
reset (mid-transaction reset is a declared coverage gap).
Tests use a deterministic memory target; error writes have no memory side effect.
The target's error policy is testbench behavior, not bridge address decoding.
Submit synthesizable SystemVerilog only; no testbench access, file I/O, simulation
termination, hierarchical references or external includes. Public tests are feedback;
final verification uses separate vectors. No access to reference or final verifier.
