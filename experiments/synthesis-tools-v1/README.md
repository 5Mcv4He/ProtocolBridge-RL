# Synthesis capability v1: reviewed evidence

This directory publishes the technical evidence for the [synthesis study](../../docs/synthesis-tools-evaluation.md). Runtime commit: `780d1827cc952ff455b0decfa487a694c35ff4ff`. It contains one real `deepseek-flash` / DSH episode on Task003 with E+synthesis-tools-v1, not a controlled efficacy comparison or parameter training run.

| Artifact | Meaning |
| --- | --- |
| `acceptance.json` | 27 real capability checks; source-bound DC/FM/PT positive and negative controls, fixed projection and independent functional failure |
| `task003-admission.json`, `admission-freeze.json` | Two legal controls, 15 mutants, 40 Policy checks and isolation; shared source SHA is the compiled control bank, variants select distinct implementations |
| `pilot-summary.json` | Audited one-episode statistics, code/model/toolchain/Policy/input hashes; Reward=0, held-out=0 |
| `representative-trajectory.json` | All 11 action events and actual allowed observations; public read bodies replaced by hashes, edited bodies stored in companion files |
| `candidate-03.sv`, `candidate-06.sv`, `candidate-10.sv` | Exact successive model-generated candidates; **all are failed candidates, not reference solutions** |
| `functional-failure-evidence.json` | Confirmed capacity violation and original result hashes; no private vectors or arbitrary raw messages |
| `final-candidate-implementation.json` | Post-hoc DC PASS and 429-point Formality PASS for the unchanged final RTL; not solver feedback or a replacement functional reward |
| `input-qualification.json`, `qualification-freeze.json` | Correct reference passes the exact reward and held-out inputs after the solver stopped; no candidate rescoring |
| `artifact-hashes.json` | SHA-256 of reviewed publication files |

The intermediate synthesis action applies to candidate06. The final RTL is candidate10, edited after the last public test. Its synthesis/equivalence result is a separate operator check. Do not collapse these into a fictitious public PASS on the final candidate.

Raw SDK responses, complete verifier/synthesis logs, executable builds, generated commercial-cell netlists, teaching library bytes, deployment configuration and private vectors remain in trusted local storage. Publication substitutions do not alter the original evidence; their original hashes are recorded. Private suite hashes support identity checks, not public access to hidden input arrays.

Use the [reproduction commands](../../docs/synthesis-tools.md#reuse) with a licensed, prepared toolchain. From a local raw episode, regenerate the summary with:

```bash
python3 scripts/synthesis_report.py .local/your-synthesis-pilot .local/new-summary.json
```

The script first audits the original episode, then writes to a new output file. Public artifacts are reviewed projections rather than a substitute for that raw audit. Historical training exchange v1/v2 does not yet accept this capability profile.
