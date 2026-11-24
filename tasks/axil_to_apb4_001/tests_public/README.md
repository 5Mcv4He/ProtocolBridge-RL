# Public development tests — revision 3

Run `python3 -m environment.test WORKSPACE NEW_OUTPUT` from the repository root.

17 cases, 132 planned transactions, including 8 deliberately reset-aborted
transactions. Active AXI4-Lite/APB4 VIP drive the actual RTL; UVM checks payloads,
responses, independent memory state, reset accounting and timing. Public vectors
use seed 17 and include a short mixed random stream. See the
[verification plan](../../../docs/verification-plan.md) for the full requirement map.

The complete regression has 22 cases and 2868 planned transactions (26 aborted),
including four 256-transaction random streams and 576 required cross bins. Real
Agent episodes use separately frozen private inputs; public tests expose the same
Spec, not every private sample. Commercial VIP and VCS remain on the licensed host.
