# Task004 v1 reviewed evidence

Source `2d29d2f2122285a4d2d9728ad73de7a95456baac`, VCS-MX O-2018.09-SP2 / AMBA VIP R-2020.12 / UVM1.2. See the [task report](../../docs/task004-evaluation-report.md) for the contract, scoreboard, failure attribution and limits.

- `quality/`: completed admission with two reference structures, 14 functional negative controls, 40 real policy mechanism checks and isolation/classification checks. Each reference passes 23 full and 21 public cases.
- `latency-control/`: extra legal delayed-response implementation passes full/public suites and 37 required bins. This is a verification control, not an Agent solution.
- `pilot/`: all four independent Agent outcomes and selected tool trajectories (A/E two each), 0/2 success in each group. Three trials produced accepted RTL edits; one submitted the template after repeated duplicate-field rejection. All outcomes retained.
- `input-qualification/`: positive reference passes all four exact paired reward/evaluation input sets after the solver trials stopped; no candidate rescoring.
- `interrupted-acceptance.json`: earlier incomplete gate correctly refused admission after a license service outage. The original run remains preserved; it is not an Agent failure and is not overwritten by the completed gate.

The batch audit passed, but 6/24 rejected actions and only one E trial with actual feedback limit interpretation. Reward 0/1/null is 4/0/0; no private reward or held-out diagnostics were returned to solving Agents. Cases stop at the first confirmed failure, so the failed candidates did not each run every case.

Raw model/EDA logs, private vectors and deployment files remain in trusted storage. Published hashes bind to retained evidence; no commercial VIP sources or credentials are included. These are fixed-model rollouts, not parameter training.
