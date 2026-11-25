# Batch analysis

All started trials remain in the denominator. Null rewards are separate from RTL failures. This is fixed-model inference, not parameter training.

| Policy | Started | Valid submissions | Success | Wilson 95% | Feedback exposed | Edited after feedback | 0 / 1 / null |
|---|---:|---:|---:|---|---:|---:|---|
| spec_only | 3 | 3 | 3 | 43.8–100.0% | 0 | 0 | 0 / 3 / 0 |
| test_verdict | 3 | 3 | 3 | 43.8–100.0% | 3 | 1 | 0 / 3 / 0 |
| test_diagnostic | 3 | 3 | 1 | 6.1–79.2% | 1 | 0 | 2 / 1 / 0 |

| Policy | First candidate public PASS / FAIL / unknown | Public calls | Changed after feedback | Format errors / actions | Tokens | Episode seconds | Request seconds | Compile seconds | Simulation seconds |
|---|---|---:|---:|---|---:|---:|---:|---:|---:|
| spec_only | 3 / 0 / 0 | 0 | 0 | 3 / 17 | 42992 | 721.4 | 46.5 | 245.4 | 422.2 |
| test_verdict | 2 / 1 / 0 | 4 | 1 | 3 / 20 | 52206 | 735.8 | 46.9 | 259.4 | 423.7 |
| test_diagnostic | 1 / 0 / 2 | 1 | 0 | 7 / 21 | 78686 | 454.6 | 57.7 | 243.4 | 148.3 |

First-candidate public measurement may be post-submit and is not extra feedback. A matching final public PASS is required before comparing public success against private failure. Request wall time includes API/network/SDK latency, not just model compute; compile/simulation durations include shell overhead. Episode time includes post-submit grading. Monetary cost is unavailable.

Quality gate: `{"passed": true, "reasons": []}`.

| Trial | Reward | Held-out | Edits | Public calls | Format errors | Failure labels (overlapping) |
|---|---:|---:|---:|---:|---:|---|
| r01-spec_only | 1.0 | 1.0 | 1 | 0 | 1 | action_protocol_error |
| r01-test_verdict | 1.0 | 1.0 | 2 | 2 | 1 | action_protocol_error |
| r01-test_diagnostic | 1.0 | 1.0 | 1 | 1 | 1 | action_protocol_error |
| r02-test_verdict | 1.0 | 1.0 | 1 | 1 | 1 | action_protocol_error |
| r02-test_diagnostic | 0.0 | 0.0 | 0 | 0 | 4 | action_protocol_error, no_effective_edit_candidate, protocol_timing_error |
| r02-spec_only | 1.0 | 1.0 | 1 | 0 | 1 | action_protocol_error |
| r03-test_diagnostic | 0.0 | 0.0 | 0 | 0 | 2 | action_protocol_error, no_effective_edit_candidate, protocol_timing_error |
| r03-spec_only | 1.0 | 1.0 | 1 | 0 | 1 | action_protocol_error |
| r03-test_verdict | 1.0 | 1.0 | 1 | 1 | 1 | action_protocol_error |

| Paired round | spec_only | test_verdict | test_diagnostic |
|---|---:|---:|---:|
| 1 | 1.0 | 1.0 | 1.0 |
| 2 | 1.0 | 1.0 | 0.0 |
| 3 | 1.0 | 1.0 | 0.0 |
