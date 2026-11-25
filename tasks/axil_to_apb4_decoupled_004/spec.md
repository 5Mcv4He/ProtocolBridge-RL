# Task 004: independent APB execution and AXI response queues (v1)

Implement one self-contained synthesizable SystemVerilog module `bridge` with the ports in the initial RTL. One clock, active-low synchronous reset; 32-bit addresses/data, four byte enables. This task differs from Task003: APB execution must continue while earlier AXI responses are waiting for consumption. Both BVALID and RVALID may be asserted simultaneously. There is one APB target and no address translation.

## Acceptance, execution and retirement

AW, W and AR each have exactly three unretired credit slots. A VALID/READY handshake occupies a slot; accepting more than three unretired entries on any channel is forbidden. AW and W arrive independently and pair FIFO by acceptance order, including W-before-AW. An AW or W credit is released only by the corresponding BVALID/BREADY handshake; an AR credit only by the corresponding RVALID/RREADY handshake. APB selection and completion do not release credits. Reset cancels all unretired credits. At most 16 consecutive rising edges may observe VALID && !READY while the pre-edge unretired count is below three; a handshake must occur before a seventeenth such edge. The counter resets when VALID is low or the channel is full. Same-edge retirement credit reuse is optional. No requirement is imposed on READY when VALID is low except that any ensuing handshake must obey capacity.

The APB executor is independent of AXI response consumption. Buffered requests have separate pending/executing/completed lifetimes. There may be up to three unconsumed write responses and three unconsumed read responses (including the response currently presented). A granted request must have its eventual response storage reserved; retaining unretired credit through retirement provides such a bound. While B is stalled, further reads and eligible writes must still execute; while R is stalled, further writes and eligible reads must still execute, subject to the three-credit bound. No extra implementation-specific response queue throttling is allowed while an eligible request exists.

## Selection and bus timing

The APB bus executes one transaction at a time. At an idle rising edge, eligibility uses only previously accepted, not-yet-selected requests: a write requires both oldest AW and oldest W, a read the oldest AR. If only one direction is eligible, select it. If both, select according to a round-robin preference initialized to READ; every grant flips preference to the opposite direction. A partial write must not block a read.

A grant must drive PSEL=1, PENABLE=0 immediately after that edge (Setup). The following edge enters Access; address/direction/data/byte-enables remain stable through Access waits. Complete Access only on PREADY=1 at a rising edge. Following that completion edge, PSEL=PENABLE=0. At the next rising edge, the executor may select the next buffered request regardless of pending AXI responses. No fall-through grant on the completion edge or on a new-request acceptance edge. Reset wins over all handshakes and clears executor, requests, response queues and arbitration preference.

## Data, responses and order

PADDR equals the full accepted AXI address. Writes map WDATA/WSTRB to PWDATA/PSTRB exactly, including zero and partial strobes; read PSTRB=0. PPROT=0. Unaligned addresses are unsupported. APB error maps to AXI SLVERR=2'b10, otherwise OKAY=2'b00. Read data and error are sampled only at APB completion; a queued read response retains that snapshot even if a later APB write changes the same address. AXI response payload and VALID remain stable until handshake. Per-direction responses must preserve FIFO request order. There is no cross-direction AXI response order requirement.

A head completed response must be presented within 16 cycles of APB completion or removal of its older response, whichever is later. This bound does not require the AXI master to assert READY. B and R can handshake on the same edge. Simultaneous enqueue/dequeue must not lose or duplicate data; long streams must wrap storage indices correctly, including non-power-of-two capacity three. Each accepted complete request executes exactly once unless interrupted by reset.

Reset cancels partial requests, executing accesses and unconsumed responses without later replay. APB writes that completed before reset remain committed at the external target, even if their B response is canceled. Other external target state is not reset by bridge reset. Inputs during asserted reset are not accepted. After reset, new traffic starts a clean ordering epoch.

## Scope

AXI4-Lite only: no bursts, IDs, exclusives, sideband AXI protection ports, multi-target routing, interrupts, CDC or width conversion. No AXI response reorder within one direction. Correctness includes the specified bounded acceptance/response latency and mandatory idle-edge selection; there is no additional throughput target or synthesis/PPA requirement. Target wait cycles and master response stalls may be arbitrary finite lengths. The verifier samples finite directed/random interleavings; passing is not a formal completeness proof.
