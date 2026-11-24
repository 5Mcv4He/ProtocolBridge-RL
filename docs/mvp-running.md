# Industrial VIP baseline: running the bridge task

The current implementation uses **active Synopsys AXI4-Lite master and APB4 slave
VIP, with a UVM reference model and scoreboard**. Python handles lifecycle, remote
VCS execution and machine-readable reward only. The former Python functional
scoreboard has been removed. The evaluation report records the current baseline and summarizes important
bring-up failures; superseded experiment files are not part of this release.

## Requirements and setup

Python 3.10+, SSH/SCP, a licensed Linux VCS and AMBA SVT installation. The remote
`~/.bashrc` initializes VCS and licensing. The tested installation is VCS
V-2023.12-SP2 / AMBA SVT R-2020.12; no commercial code or license is distributed.
Prepare generated VIP projects on the licensed host:

```bash
bash environment/setup-vip.sh /your/new/generated-projects
```

Copy `environment/config.example.json` to `.local/config.json`; set `vip_root` to
its APB project, `axi_vip_root` to its AXI project, and configure the remaining SSH
and installation paths. `PB_CONFIG` may select an alternate absolute config path.
The compile command sets the required UVM packer size and single-port VIP limits.

## Running (repository root)

```bash
python3 -m environment.reset .local/solve-001
# Edit .local/solve-001/bridge.sv
python3 -m environment.test .local/solve-001 .local/public-001
python3 -m environment.submit .local/solve-001 .local/submission-001

bash environment/reproduce.sh .local/reproduction-001

# Real model trial requires DeepSeek Harness SDK/runtime 0.2.2rc2 and
# DEEPSEEK_API_KEY supplied from your own secret store.
export PB_AGENT_PYTHON=/path/to/harness-python
bash environment/reproduce.sh .local/reproduction-002 --agent
```

All output paths must be new. Public and final vector sets use different seeds.
A repeated model trial is stochastic; replaying submitted RTL needs no model API.

## Verification path

1. A constrained VIP master sequence plans one transaction and waits for its
   completion before issuing another; AW/W are independently driven by the VIP.
2. Active APB slave VIP supplies data, wait states and errors. Its memory receives
   actual completed APB monitor transactions.
3. UVM Scoreboard receives a cloned planned request, AXI VIP monitor completion,
   and APB VIP monitor completion through analysis ports. It maintains its own
   independent expected memory and checks payloads, strobes, errors, ordering and
   exact completion counts.
4. Pin-level assertions supplement VIP checks with task-specific latency,
   response stability, reset and APB sequencing requirements. Actual pin events
   count AW-first/W-first/simultaneous, waits, stalls, early-ready and resets.
5. Python reads the UVM structured result and report summary. It does not compute
   expected transaction values or compare payloads. A nominal pass with missing
   required stimulus bins is incomplete (`reward=null`), not a functional pass.

`1.0` requires complete UVM transaction checking and zero verification errors.
Confirmed compile, timing, semantic and cycle-timeout errors return `0.0`.
Tool/license failures, incomplete verification and ambiguous failures return `null`.
Wall-clock timeout is infrastructure/indeterminate; the explicit cycle watchdog
is a DUT progress failure when the initialized environment is functioning.

## Controls and isolation

Mutation regression compiles a bank of actual reference/faulty RTL modules once,
then starts a fresh simulation for each selection. Only selected outputs reach
VIP; the scoreboard has no access to selection and uses the same rules for all.
This reduces repeated commercial VIP compilation under UTM. Agent submissions
are compiled alone, never in the control bank. If the submitted source and frozen
verification inputs match a prior public build exactly, the compiled simulation is
copied to a fresh remote directory and run with final vectors; otherwise it is
compiled anew. Final scoring always runs a new simulation. A configurable VCS
`compile_cache` can provide shared incremental objects; VCS checks dependencies.

Task, evaluator, environment and fixtures are hashed before model execution. Only
read/edit of allowed solver files, public test and submit are exposed to the
solver. Full external model events and simulator logs remain private; reviewed
source, action traces, counts and result hashes are exported.

This is **not OS security isolation**, secure hidden tests, synthesis proof or
industrial signoff. The public repository exposes test generation and fixtures.
A hardened execution sandbox and genuinely private holdout are still needed for
adversarial benchmarking. Mid-transaction reset/abort testing and wider protocol
features are not silently implied by using commercial VIP.
