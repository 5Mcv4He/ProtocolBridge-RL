> Historical revision 2 report. It does not establish revision 3 acceptance.

# Active AMBA VIP / UVM baseline evaluation

Date: 2026-11-24. **Active-VIP UVM single-task baseline acceptance completed.**
The earlier Python scoreboard was removed at the user's request. Historical v1
results are not reused as current PASS evidence.

For implementation explanations, see [architecture and scoreboard](../../docs/architecture.md),
[Agent execution and reward](../../docs/agent-workflow.md), and [reproduction commands](../../docs/mvp-running.md).
This report records measured results; those guides explain how the current code produces them.

## Implemented architecture

- VCS V-2023.12-SP2, AMBA SVT R-2020.12, active AXI4-Lite master + APB4 slave.
- UVM sequences drive requests and target responses. Both VIP monitors feed
  analysis ports into an original UVM scoreboard.
- Three-way comparison: planned request, observed AXI completion, observed APB
  transfer. Expected byte-addressed register state and actual target memory are
  maintained separately. Addresses, direction, write data/strobes, read data,
  response errors, order and counts are checked during simulation.
- Supplementary pin assertions enforce task-specific stability, synchronous reset
  and 16-cycle latency bounds. Actual signal coverage distinguishes AW/W arrival
  order, same-cycle handshakes, APB waits, response stalls and early READY.
- Python only generates stimulus, orchestrates VCS and maps structured UVM verdicts
  into reward; no Python functional scoreboard remains.

## Verification scope

One clock, 32-bit addresses/data, aligned requests, one outstanding operation,
independent AW/W, APB4 byte strobes, wait/error handling and AXI backpressure.
Public/final suites have different seeds. Repeated partial writes test accumulated
memory state; initial and between-transaction resets are included. No concurrent
read/write traffic outside the explicit task contract is generated.

## Measured results

Correct reference: 128 planned requests, 128 AXI VIP completions, 128 APB VIP
completions, 128 checked, zero UVM scoreboard errors and zero UVM errors/fatals.
Actual pin coverage: AW-first 21, W-first 21, simultaneous 22; response-stall cycles
602; early-ready completions 16; APB wait cycles 202; between-transaction resets 8.
The AW/W ordering counts sum to 64 writes; waits/stalls count cycles, not cases.
All six RTL mutants were actually rejected: address, WSTRB, PSLVERR and read-data
mutants by UVM semantic checking; PREADY and response-stability mutants by timing
checking. All completed 128 observed transactions on both VIP monitors.
The address mutant generated 111 UVM scoreboard errors and no protocol errors.
The response-instability mutant generated **301 AXI VIP protocol errors plus 301
original timing assertion errors**. The PREADY mutant generated **7,164 APB/AXI
VIP protocol errors**, 652 original timing errors and 24 scoreboard errors. These
are repeated report counts, not distinct bug types or numbers of test cases.
Thus both commercial protocol checking and cross-protocol semantic checking have
been exercised by actual negative controls.
A fresh model trial completed successfully after repairing a Harness response-format issue;
[the failed Harness attempt](../harness-format-failure/README.md) is
preserved as null and is not counted as an RTL failure.

The first completed integration build terminated at time zero because the AXI VIP requires
UVM_PACKER_MAX_BYTES=1500000. It was recorded as infrastructure/null. The compile
configuration was corrected; no zero-transaction run is considered a PASS.
Further bring-up found the APB compile-time width default (8 bits), required
AXI4-Lite signal-disable settings, and a slave sequence constraint conflict from
trying to randomize observed write data. The fixes explicitly set 32-bit widths,
validate them at startup, configure Lite-only signals, and set APB response fields
without overwriting observed write data. These bring-up runs retain null rewards. See [bring-up records](../vip-bringup.json).

A subsequent reference run completed all 128 AXI/APB transactions with zero UVM
scoreboard errors, but observed zero response-stall cycles. The coverage gate
correctly returned null. READY defaults are now dynamically reconfigured through
the VIP API, and the corrected reference has now reached all required bins and passed.

## Evidence and reproduction

See [run instructions](../../docs/mvp-running.md). Raw model/simulator artifacts remain
under `.local/`; only reviewed original source, JSON results, tool traces and
project-generated event lines are exportable. Commercial source and licensing
material remain exclusively on the licensed host.

## Remaining technical boundaries

Using industrial VIP does not establish industrial signoff. Mid-transaction
reset/abort coverage, formal/synthesis checks, independent tool cross-checks and
exhaustive protocol/interleaving coverage remain separate work. Multiple fresh
model trials are needed to estimate task difficulty; a single pass is not an
estimate of Agent reliability. OS sandboxing and secure private holdout are not
implemented. A finite suite's reward is bounded by its checked behavior.

## Scope of the acceptance claim

Implemented and exercised so far: active AXI/APB VIP, monitor analysis-port
connections, UVM semantic reference/scoreboard, pin assertions, required observed
stimulus bins, reference and six negative RTL controls. Infrastructure null paths
were also exercised by genuine bring-up failures.

Implemented but not separately fault-injected: submitted syntax-error classification
and the explicit global cycle-watchdog category. A real Agent trial and final artifact-copy replay have completed successfully.
The copied executable ran in a distinct remote directory with final vectors; source
and UVM input hashes were unchanged, and final reward was 1.0.

Not implemented: OS sandbox/private secure holdout, mid-transaction reset-abort
coverage, exhaustive VIP coverage closure, synthesis/formal verification, or
statistical evaluation of Agent success rate. The supported task remains a bounded
single-outstanding bridge; additional concurrency must first change its Spec.

## Completed Agent trial and evidence

Model: `deepseek-flash`, official provider via DeepSeek Harness SDK/runtime
0.2.2rc2, reasoning disabled. The solver received only the Spec, stub and public
tool feedback. It performed six real capability actions:

`read spec → read RTL → edit → edit → public test → submit`.

The two edits preceded testing; there was **no failed-RTL feedback repair cycle**.
Public test: 32 AXI/APB transactions, 136 observed stall cycles, zero errors.
Independent final simulation: 128 AXI/APB transactions, 602 stall cycles, 202 APB
wait cycles, all required bins reached, zero scoreboard/verification errors,
**reward=1.0**. Final source SHA-256:
`3acfb67892ffc8d0d504a657e38c41de4c07fa17857b10c2bff8d80ffdb49a31`.

Task and evaluator hashes were unchanged across the trial. Compilation was reused
only after input hashes matched; final simulation ran in a different directory
with a separate vector set. This is reproducible execution separation, not OS
security isolation. Full external Harness responses and raw VCS evidence remain
in `.local/agent-industrial-02/` and `.local/v2-controls-05/`.

Reviewed public evidence:

- [Control results](controls-summary.json)
- [Agent actions and feedback (compact trace; repeated source bodies use hashes)](agent/trace.json)
- [Final reward](agent/result.json)
- [Final submitted RTL](agent/final.sv)
- [Frozen source manifest](agent/freeze.json)
- [Reference event evidence](controls/reference/events.txt)
- [AXI VIP negative-control counters](controls/bad_backpressure/result.json)

Each exported run includes original event lines, actual counts and raw-evidence
hashes; commercial logs, libraries and credentials are not exported.

## What this says about task difficulty

A fresh model still passed after stronger verification. That is a valid result,
not a reason to force failure. This restricted single-outstanding bridge is a
small state-machine task that a capable coding model can solve. The six rejected
faults establish sensitivity to those fault classes; they do not prove exhaustive
correctness. One successful design trial cannot estimate a model success rate.
Harder supported scenarios require explicit Spec changes and separate repeated
trials, rather than silently testing unsupported concurrency.

## Minimal reproduction

Configure the licensed host following [running instructions](../../docs/mvp-running.md),
then use `bash environment/reproduce.sh NEW_OUTPUT_DIRECTORY --agent` with
`PB_AGENT_PYTHON` and `DEEPSEEK_API_KEY` configured. The control-only command omits
`--agent`. To replay the submitted source without an API call:

```bash
python3 -m verifier.grade experiments/industrial-v2/agent/final.sv .local/replay-industrial-001
```
