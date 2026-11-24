# AXI4-Lite to APB4 — task 001, revision 3

Implement the synthesizable SystemVerilog module `bridge` with exactly the ports
in `bridge.sv`. This is one AXI4-Lite slave connected to one APB4 master target.

## Clock, reset and supported traffic

- All transfers use the rising edge of `clk`; `rst_n` is active-low synchronous reset.
- Address and data widths are 32 bits. Addresses are byte addresses aligned to four
  bytes; pass every address bit unchanged. There is no bridge address decoding.
- There is one outstanding transaction. The requester starts its next transaction
  only after the preceding B/R handshake, or after reset cancels it. Read and write
  requests do not overlap. Repeated reads, repeated writes and arbitrary direction
  changes between completed transactions are supported.
- There are no bursts, IDs, exclusives, clock crossings or AWPROT/ARPROT ports.
  Drive APB PPROT to 000.

## AXI request acceptance

- AW and W can arrive together or in either order, with arbitrary finite gaps.
  Accepting AW must not require WVALID, and accepting W must not require AWVALID.
- The requester keeps VALID and payload stable until READY. Buffer each accepted
  write half once; do not execute a write before accepting both halves.
- When idle and able to accept the next transaction, accept each offered channel
  within 16 cycles. After accepting both AW/W, or accepting AR, begin APB setup
  within 16 cycles. These bounds do not bound the gap between independently
  offered AW and W or the target/requester's externally imposed wait time.

## APB conversion and AXI response

- Each non-aborted AXI request produces exactly one APB transfer: one setup cycle
  with PSEL=1/PENABLE=0, followed by access with PSEL=PENABLE=1 until PREADY=1.
- Address, direction, write data, strobe and protection remain stable through
  setup/access/wait. Support any finite number of PREADY wait cycles.
- For writes, map WDATA and all four WSTRB bits unchanged, including WSTRB=0000.
- For reads, drive PWRITE=0 and PSTRB=0; PWDATA has no functional meaning.
- Sample PRDATA and PSLVERR only at APB completion. Map PSLVERR=0 to OKAY (00)
  and PSLVERR=1 to SLVERR (10). RDATA equals completed PRDATA even on an error.
- BVALID/RVALID cannot precede APB completion and must assert within 16 cycles
  of it. Preserve VALID and response payload until BREADY/RREADY, including long
  backpressure. Do not launch another APB transfer while a response is pending.

## Reset at any transaction stage

At a rising edge with rst_n=0, clear buffered request halves and pending responses,
and drive PSEL/PENABLE/BVALID/RVALID low. The requester and target are reset too.

- A request interrupted before APB completion is discarded without an AXI response.
- If APB completed before reset but the AXI response was still pending, discard
  that response. A completed external APB write is not rolled back by bridge reset.
- The test target retains already committed memory across reset; an interrupted
  APB write has no memory side effect. This is target behavior, not bridge storage.
- After reset release, the bridge must accept new requests without stale data,
  ghost responses or old buffered request halves.

## Target behavior and submission rules

Tests use an independently modeled memory target. Successful partial writes update
selected bytes; error writes have no memory effect. Target errors and waits are
controlled by the environment, independently of bridge address decoding.

Submit one self-contained `bridge` module. No external includes/modules, compiler
macros, hierarchical references, string literals, initial/final blocks, DPI,
file I/O or simulation control. System functions are limited to `$clog2` and
`$bits`. This restricted synthesizable subset is enforced before compilation.

Public tests provide representative examples and feedback. Private reward and
reserved evaluation inputs test the same Spec, including boundary combinations;
they add no hidden functional requirements. The solver must not access the
reference implementation or evaluator. Performance/area optimization is not
part of the current functional reward.
