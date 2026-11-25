# Batch analysis

All started trials remain in the denominator. Null rewards are separate from RTL failures. This is fixed-model inference, not parameter training.

| Policy | Started | Valid submissions | Success | Wilson 95% | Feedback exposed | Edited after feedback | 0 / 1 / null |
|---|---:|---:|---:|---|---:|---:|---|
| spec_only | 2 | 2 | 0 | 0.0–65.8% | 0 | 0 | 2 / 0 / 0 |
| test_diagnostic | 2 | 2 | 0 | 0.0–65.8% | 1 | 1 | 2 / 0 / 0 |

| Policy | First candidate public PASS / FAIL / unknown | Public calls | Changed after feedback | Format errors / actions | Tokens | Episode seconds | Request seconds | Compile seconds | Simulation seconds |
|---|---|---:|---:|---|---:|---:|---:|---:|---:|
| spec_only | 0 / 2 / 0 | 0 | 0 | 1 / 9 | 26748 | 209.4 | 25.6 | 168.9 | 10.9 |
| test_diagnostic | 0 / 1 / 1 | 2 | 1 | 5 / 15 | 95638 | 244.8 | 64.1 | 168.1 | 9.3 |

First-candidate public measurement may be post-submit and is not extra feedback. A matching final public PASS is required before comparing public success against private failure. Request wall time includes API/network/SDK latency, not just model compute; compile/simulation durations include shell overhead. Episode time includes post-submit grading. Monetary cost is unavailable.

Quality gate: `{"passed": true, "reasons": []}`.

| Trial | Reward | Held-out | Edits | Public calls | Format errors | Failure labels (overlapping) |
|---|---:|---:|---:|---:|---:|---|
| r01-spec_only | 0.0 | 0.0 | 1 | 0 | 1 | action_protocol_error, protocol_timing_error |
| r01-test_diagnostic | 0.0 | 0.0 | 0 | 0 | 5 | action_protocol_error, no_effective_edit_candidate, protocol_timing_error |
| r02-test_diagnostic | 0.0 | 0.0 | 2 | 2 | 0 | protocol_timing_error, repair_after_feedback_failed |
| r02-spec_only | 0.0 | 0.0 | 1 | 0 | 0 | protocol_timing_error |

| Paired round | spec_only | test_diagnostic |
|---|---:|---:|
| 1 | 0.0 | 0.0 |
| 2 | 0.0 | 0.0 |
