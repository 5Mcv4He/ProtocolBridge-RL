# Batch analysis

All started trials remain in the denominator. Null rewards are separate from RTL failures. This is fixed-model inference, not parameter training.

| Policy | Started | Valid submissions | Success | Wilson 95% | Feedback exposed | Edited after feedback | 0 / 1 / null |
|---|---:|---:|---:|---|---:|---:|---|
| spec_only | 6 | 5 | 5 | 43.6–97.0% | 0 | 0 | 0 / 5 / 1 |
| test_verdict | 5 | 5 | 4 | 37.6–96.4% | 5 | 1 | 1 / 4 / 0 |
| test_diagnostic | 6 | 6 | 1 | 3.0–56.4% | 3 | 1 | 5 / 1 / 0 |

| Policy | First candidate public PASS / FAIL / unknown | Public calls | Changed after feedback | Format errors / actions | Tokens | Episode seconds | Request seconds | Compile seconds | Simulation seconds |
|---|---|---:|---:|---|---:|---:|---:|---:|---:|
| spec_only | 4 / 1 / 1 | 0 | 0 | 16 / 51 | 279221 | 1324.8 | 146.9 | 490.2 | 675.0 |
| test_verdict | 3 / 1 / 1 | 7 | 1 | 7 / 34 | 90469 | 1084.1 | 80.0 | 421.9 | 572.6 |
| test_diagnostic | 1 / 1 / 4 | 4 | 1 | 18 / 48 | 183382 | 962.2 | 135.4 | 652.1 | 164.5 |

First-candidate public measurement may be post-submit and is not extra feedback. A matching final public PASS is required before comparing public success against private failure. Request wall time includes API/network/SDK latency, not just model compute; compile/simulation durations include shell overhead. Episode time includes post-submit grading. Monetary cost is unavailable.

Quality gate: `{"passed": false, "reasons": ["widespread_protocol_blocked_edits", "protocol_error_action_rate_above_30_percent"]}`.

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
| r04-spec_only | 1.0 | 1.0 | 1 | 0 | 2 | action_protocol_error |
| r04-test_verdict | 0.0 | 0.0 | 0 | 2 | 3 | action_protocol_error, no_effective_edit_candidate, protocol_timing_error |
| r04-test_diagnostic | 0.0 | 0.0 | 0 | 0 | 3 | action_protocol_error, no_effective_edit_candidate, protocol_timing_error |
| r05-test_verdict | 1.0 | 1.0 | 1 | 1 | 1 | action_protocol_error |
| r05-test_diagnostic | 0.0 | 0.0 | 3 | 2 | 1 | action_protocol_error, protocol_timing_error, repair_after_feedback_failed |
| r05-spec_only | None | None | 0 | 0 | 10 | action_protocol_error, no_effective_edit_candidate, agent_incomplete |
| r06-test_diagnostic | 0.0 | 0.0 | 0 | 1 | 7 | action_protocol_error, no_effective_edit_candidate, protocol_timing_error |
| r06-spec_only | 1.0 | 1.0 | 2 | 0 | 1 | action_protocol_error |

| Paired round | spec_only | test_verdict | test_diagnostic |
|---|---:|---:|---:|
| 1 | 1.0 | 1.0 | 1.0 |
| 2 | 1.0 | 1.0 | 0.0 |
| 3 | 1.0 | 1.0 | 0.0 |
| 4 | 1.0 | 0.0 | 0.0 |
| 5 | None | 1.0 | 0.0 |
| 6 | 1.0 | not started | 0.0 |
