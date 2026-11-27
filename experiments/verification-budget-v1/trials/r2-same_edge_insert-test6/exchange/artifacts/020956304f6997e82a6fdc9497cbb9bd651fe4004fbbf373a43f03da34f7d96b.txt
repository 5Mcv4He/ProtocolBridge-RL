# AXI4-Lite to APB4 with bounded request queues — x2p_queue_three_v1 — queue family v1

Implement one self-contained synthesizable module `bridge`, with exactly the ports
in the initial RTL. All signals use rising-edge `clk`; `rst_n` is active-low
synchronous reset. Address/data widths are 32 bits, addresses are byte addresses
aligned to four bytes. There is one APB target, no address decoding: pass all
address bits unchanged. There are no bursts, IDs, exclusives, clock crossings,
interrupts, AWPROT or ARPROT ports. PPROT=000 during transfers.

## Queue capacity and acceptance

The requester may overlap reads and writes and may issue later requests before
receiving earlier responses. It preserves FIFO order on each AXI request channel.
The first accepted AW pairs with the first accepted W, the second with the second,
and so on. AW and W may be separated by arbitrary finite gaps in either direction.

- Store up to 3 accepted AW and 3 accepted W payloads independently.
  Only a B response handshake retires one AW and W credit. Executing writes and
  pending B responses retain both credits. A partial write occupies its own half.
- Store up to 3 accepted AR payloads, retained until the R response handshake.
- Maximum complete unretired writes is 3, reads is 3; the directions have
  separate capacity. Reset cancels all credits. Depth one requires no rotating
  storage index; depth three must handle non-power-of-two wrap correctly.
- AWREADY must not depend on WVALID or the presence of the matching W half;
  WREADY must not depend on AWVALID or AW acceptance. AR acceptance is independent
  of writes. Acceptance must continue while APB or an AXI response is stalled if
  the corresponding channel still has capacity.
- Accept an offered channel within 16 cycles while its credit is available.
  Time for which its queue is full does not count toward this bound. VALID and
  payload are held by the requester until READY. Both conservative READY (new
  credit visible next cycle) and same-edge response-credit reuse are legal.
- Never exceed the per-channel unretired capacities declared above. Do not overwrite, drop or duplicate
  accepted requests. Read and write responses remain FIFO ordered within their
  own direction; there is no required global order between reads and writes.

## Serial APB execution and round-robin selection

Only one transaction executes on APB at a time. A write is eligible when both its
oldest unretired AW and W are buffered. A read is eligible when its oldest AR is
buffered. A partial write must not block eligible reads.

Selection uses a registered FIFO contract:

1. At an edge when no transaction is executing or awaiting response consumption,
   inspect requests buffered BEFORE that edge. Newly accepted requests at that
   same edge become eligible at the following edge (no input-to-APB bypass).
2. If at least one request is eligible, start its APB setup during the cycle
   immediately following that edge. With both directions eligible, choose the
   current round-robin preference; otherwise choose the eligible direction.
3. Preference starts with READ after reset. Every selection changes preference
   to the opposite of the selected direction, including selections that later
   return an APB error. No further selection occurs until its AXI response is
   consumed. A response consumed on the current edge makes the executor idle for
   the NEXT edge; it cannot select and consume a response on the same edge.

Thus, for an otherwise idle bridge, a request accepted on edge N can first be
selected on edge N+1, drives setup in the following cycle, and presents setup to
the APB target on edge N+2. These explicit scheduling rules make arbitration
observable and reproducible; they are not a requirement for speculative bypass.

## APB and AXI response behavior

- Each selected non-aborted request produces exactly one APB setup cycle with
  PSEL=1/PENABLE=0, then access with both high until PREADY=1.
- Keep address, write direction, write data, PSTRB and PPROT stable through
  setup/access/wait. Support any finite target wait. For writes pass WDATA and
  every WSTRB bit unchanged, including zero. For reads PSTRB=0.
- Only at APB completion sample PRDATA and PSLVERR. Return OKAY (00) for no error
  and SLVERR (10) for an error; RDATA must equal PRDATA even on an error.
- BVALID/RVALID cannot precede the corresponding APB completion and must assert
  within 16 cycles after it. Preserve VALID and payload until READY, even with
  long response backpressure or READY already high before VALID.
- The executor holds that response until consumed. Do not start another APB
  transfer while it is pending, even if the other response channel is ready.
  Request queues may still fill independently during this time.
- While no APB transfer is active, PSEL=PENABLE=0. Other APB payload outputs have
  no functional meaning. No throughput/area optimization beyond the stated
  scheduling and acceptance behavior is part of the reward.

## Reset and target memory

At every rising edge with rst_n=0, clear all queued AW/W/AR requests, partial
writes, in-flight state, pending B/R responses and arbitration preference (READ).
Drive PSEL/PENABLE/BVALID/RVALID low. The requester and target are reset too.
No queued or interrupted request may generate a stale APB transfer or response
after reset release. Accept new traffic normally after release.

A write already completed on APB remains committed even if its AXI response or
later queued requests are discarded by reset. An interrupted APB transfer has no
memory effect. Each successful APB write updates only bytes selected by PSTRB;
error writes do not update target memory. These are test-target behaviors, not
requirements to implement memory inside the bridge. The target retains committed
memory across reset.

## Submission and evaluation boundary

Submit only the `bridge` module. No external modules/includes, compiler directives,
hierarchical access, string literals, initial/final blocks, DPI, file I/O or
simulation control. System functions are limited to `$clog2` and `$bits`.

Public, private reward and reserved evaluation exercise this same contract. Only
Policy-allowed public feedback is visible during solving. Reference RTL, verifier
source and private inputs are not available to the solving process. Formal proof,
synthesis, complete code coverage and an assertion of all possible-input
correctness are outside the current functional evaluation.
