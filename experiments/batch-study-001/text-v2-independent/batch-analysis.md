# Batch analysis

All started trials remain in the denominator. Null rewards are separate from RTL failures. This is fixed-model inference, not parameter training.

| Policy | Started | Valid submissions | Success | Wilson 95% | Feedback exposed | Edited after feedback | 0 / 1 / null |
|---|---:|---:|---:|---|---:|---:|---|
| spec_only | 10 | 10 | 7 | 39.7–89.2% | 0 | 0 | 3 / 7 / 0 |
| test_verdict | 10 | 10 | 8 | 49.0–94.3% | 9 | 2 | 2 / 8 / 0 |
| test_diagnostic | 10 | 10 | 8 | 49.0–94.3% | 7 | 2 | 2 / 8 / 0 |

| Policy | First candidate public PASS / FAIL / unknown | Public calls | Changed after feedback | Format errors / actions | Tokens | Episode seconds | Request seconds | Compile seconds | Simulation seconds |
|---|---|---:|---:|---|---:|---:|---:|---:|---:|
| spec_only | 7 / 3 / 0 | 0 | 0 | 0 / 44 | 98810 | 2320.7 | 104.8 | 1158.4 | 1039.3 |
| test_verdict | 8 / 2 / 0 | 11 | 2 | 0 / 53 | 131645 | 2317.5 | 116.9 | 978.5 | 1203.0 |
| test_diagnostic | 6 / 4 / 0 | 10 | 2 | 2 / 56 | 156599 | 2404.6 | 124.3 | 996.5 | 1264.2 |

First-candidate public measurement may be post-submit and is not extra feedback. A matching final public PASS is required before comparing public success against private failure. Request wall time includes API/network/SDK latency, not just model compute; compile/simulation durations include shell overhead. Episode time includes post-submit grading. Monetary cost is unavailable.

Quality gate: `{"passed": true, "reasons": []}`.

| Trial | Reward | Held-out | Edits | Public calls | Format errors | Failure labels (overlapping) |
|---|---:|---:|---:|---:|---:|---|
| r01-spec_only | 1.0 | 1.0 | 1 | 0 | 0 | none |
| r01-test_verdict | 1.0 | 1.0 | 1 | 1 | 0 | none |
| r01-test_diagnostic | 1.0 | 1.0 | 1 | 0 | 0 | none |
| r02-test_verdict | 1.0 | 1.0 | 1 | 0 | 0 | none |
| r02-test_diagnostic | 1.0 | 1.0 | 1 | 0 | 0 | none |
| r02-spec_only | 1.0 | 1.0 | 2 | 0 | 0 | none |
| r03-test_diagnostic | 1.0 | 1.0 | 2 | 1 | 1 | action_protocol_error |
| r03-spec_only | 1.0 | 1.0 | 1 | 0 | 0 | none |
| r03-test_verdict | 0.0 | 0.0 | 2 | 2 | 0 | protocol_timing_error, repair_after_feedback_failed |
| r04-spec_only | 1.0 | 1.0 | 1 | 0 | 0 | none |
| r04-test_verdict | 1.0 | 1.0 | 1 | 1 | 0 | none |
| r04-test_diagnostic | 0.0 | 0.0 | 1 | 0 | 0 | protocol_timing_error |
| r05-test_verdict | 1.0 | 1.0 | 1 | 1 | 0 | none |
| r05-test_diagnostic | 1.0 | 1.0 | 2 | 2 | 0 | none |
| r05-spec_only | 1.0 | 1.0 | 2 | 0 | 0 | none |
| r06-test_diagnostic | 1.0 | 1.0 | 1 | 1 | 1 | action_protocol_error |
| r06-spec_only | 0.0 | 0.0 | 1 | 0 | 0 | protocol_timing_error |
| r06-test_verdict | 1.0 | 1.0 | 2 | 2 | 0 | none |
| r07-spec_only | 0.0 | 0.0 | 2 | 0 | 0 | protocol_timing_error |
| r07-test_verdict | 1.0 | 1.0 | 1 | 1 | 0 | none |
| r07-test_diagnostic | 1.0 | 1.0 | 2 | 1 | 0 | none |
| r08-test_verdict | 0.0 | 0.0 | 1 | 1 | 0 | protocol_timing_error |
| r08-test_diagnostic | 0.0 | 0.0 | 1 | 2 | 0 | protocol_timing_error |
| r08-spec_only | 1.0 | 1.0 | 1 | 0 | 0 | none |
| r09-test_diagnostic | 1.0 | 1.0 | 1 | 1 | 0 | none |
| r09-spec_only | 1.0 | 1.0 | 1 | 0 | 0 | none |
| r09-test_verdict | 1.0 | 1.0 | 1 | 1 | 0 | none |
| r10-spec_only | 0.0 | 0.0 | 2 | 0 | 0 | protocol_timing_error |
| r10-test_verdict | 1.0 | 1.0 | 1 | 1 | 0 | none |
| r10-test_diagnostic | 1.0 | 1.0 | 2 | 2 | 0 | none |

| Paired round | spec_only | test_verdict | test_diagnostic |
|---|---:|---:|---:|
| 1 | 1.0 | 1.0 | 1.0 |
| 2 | 1.0 | 1.0 | 1.0 |
| 3 | 1.0 | 0.0 | 1.0 |
| 4 | 1.0 | 1.0 | 0.0 |
| 5 | 1.0 | 1.0 | 1.0 |
| 6 | 0.0 | 1.0 | 1.0 |
| 7 | 0.0 | 1.0 | 1.0 |
| 8 | 1.0 | 0.0 | 0.0 |
| 9 | 1.0 | 1.0 | 1.0 |
| 10 | 0.0 | 1.0 | 1.0 |
