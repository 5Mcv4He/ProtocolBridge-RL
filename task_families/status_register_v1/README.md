# 硬件／软件共享状态任务族

同周期硬件置位与软件写 1 清除谁优先，是可以独立改变、必须明确验证的工程契约。本族生产两个 8 位任务：`set_dominant` 与 `clear_dominant`，分别以相反优先级的人工缺陷作为起点。

```bash
python3 -m task_families.status_register_v1.generate set_dominant NEW_CANDIDATE_DIR
python3 -m verifier.status_register.quality NEW_GATE_DIR
python3 -m verification_resources.production_v3 produce status-register set-dominant NEW_PACKAGE
```

可信判据是独立参考 Formality 加逐位真值表 VCS。候选和参考一致不足以审查 Spec，因此两种合法结构及所有错误对照也单独接受真值表核对。异步复位与未完成比较不能被忽略，没有 PPA 奖励。

[置位优先规格](../../tasks/status_set_dominant_repair_v1/spec.md)、[39 项真实验收](../../experiments/task-production-v2/status-quality-v1.json)和[两条实际试次](../../experiments/task-production-v2/status-study-results.json)分开记录工程要求、准入与校准。一个失败试次没有有效编辑，不能把它当作 RTL 修复能力的充分测量。
