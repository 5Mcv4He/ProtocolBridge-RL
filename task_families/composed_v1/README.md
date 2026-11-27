# Route × retirement composition v1

This producer specializes one reviewed contract: three APB targets and two unretired credits per AXI request channel. The new capability is preserving target identity and DECERR lifecycle under queued traffic, not increasing random seed count.

Start with the [contract and verification explanation](../../docs/composed-task-production.md). Generate with `python3 -m task_families.composed_v1.generate OUT`. Every output is candidate-only until its own source-matched industrial Quality Gate accepts it. Historical task families are unchanged.

The task contract remains version 1; the current verifier is revision 2. The [same-source reset counterexample and corrected admission](../../docs/composed-environment-evaluation.md) explain why the initial all-pass coverage result was insufficient.
