# 固定流程结构优化证据

本目录交付一个功能保持的位计数优化任务、真实15项质量门禁、一条预声明模型失败轨迹及重放审计。报告见[功能优先的结构优化](../../docs/bitfold-optimization-evaluation.md)。商业库、原始工具日志、运行部署与私有输入保留在可信本地环境。

- `feasibility.json`：定义任务之前的六次结构可行性测量。
- `quality.json`：源码、库、正反对照及真实工具运行摘要。
- `session-acceptance.json`：两次完整评分经Session v6返回白名单测量，测试预算／提交冻结检查；材料化缺失文件与依赖拒绝。
- `study-plan.json`／`study-results.json`：冻结条件与全部1条实际启动试次。
- `replay-audit.json`／`exchange/`：真实提案、执行、送达反馈、源码演变、训练奖励及独立保留分区。
- `costs.json`：开发探针、门禁和模型求解成本分别记录。

## 从准入到实际运行

需要Python 3.10+，以及[工具配置](../../docs/toolchain.md)中经授权、与此证据匹配的VCS/DC/Formality和教学库。以下检查与材料化不启动模型，也不重跑EDA：

```bash
python3 -m verification_resources.production_v8 materialize population-budget22 .local/new-structure-package
python3 -m verification_resources.production_v8 check .local/new-structure-package
python3 -m environment.artifact_task.cli_v4 reset bitfold_cell_budget_v1 .local/new-structure-work
```

实际工具验收必须使用新的输出目录；不会覆盖历史证据：

```bash
python3 -m verifier.bitfold_optimization.quality .local/new-structure-quality
python3 -m environment.artifact_task.cli_v4 test bitfold_cell_budget_v1 .local/new-structure-work .local/new-structure-test
python3 -m environment.artifact_task.cli_v4 submit bitfold_cell_budget_v1 .local/new-structure-work .local/new-structure-submit
python3 -m unittest tests.test_bitfold_optimization tests.test_native_trajectory_uses
```

真实模型入口为 `environment.native_tools.run_v6`，沿用已验收的native v3安装与凭据环境。新研究须复制计划、明确新试次身份并重新冻结实际源码，不复用旧试次目录或把重新运行写成历史结果。每次启动核对安装来源和隔离探针；提交后先确认求解结束，再终局评分与保留评估。

完整原始事件可在可信侧重放，重放不会运行模型或EDA：

```bash
python3 -m scripts.check_native_replay_v4 /path/to/private/trial --out /path/to/new-audit.json
```

[公开v9交换](exchange/manifest.json)可用于复核候选与反馈；完整本地重放所需原始运行事件并未全部公开。公开入口不承诺没有商业工具也能重新执行工业验收。
