# Engineering tools v1 evidence

Four paired Task003 repair rollouts: two original E, two E with bounded compiler and public invariant queries. All four valid submissions received reward 0; no format or infrastructure failures. Both enhanced trials actually queried the capacity invariant. See [research report](../../docs/engineering-tools-evaluation.md).

- `baseline/`, `tools/`: separate complete outcome tables and all four selected tool trajectories, candidate RTL and provenance.
- `study-report.json`: matched-variable audit, actual feedback exposure, costs and descriptive intervals.
- `task003-quality/`: exact-source requalification, two references and 15 negative controls.
- `input-qualification/`: positive reference over the exact four paired private/held-out inputs.
- `exchange-validation.json`: actual v2 export, 4 records/4 trajectories, separate held-out records, and Python 3.6/current compatibility checks. Regenerate using the [data contract](../../docs/rollout-data-contract.md).
- `mechanism.json`, `compiler-infrastructure-probe.json`, `tool-probes.json`: tool boundaries and actual capability probes.

Raw DSH responses, vendor logs, deployment configuration and private vectors remain in trusted storage. Published hashes link to them without exposing their contents. These results are fixed-model inference, not parameter training. Historical cohorts remain unchanged.
