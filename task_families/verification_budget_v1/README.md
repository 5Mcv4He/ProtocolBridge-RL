# 同一工程环境，两种公开验证额度

这个生产入口建立一次受控预算研究的环境包，不增加 RTL Task。它保留三深度队列的 Spec、验证器、参考实现及九种工具，仅增加版本化的公开 test 额度选择：2 次或 6 次。两组总动作上限仍为 20，反馈和其他工具预算不变。

```bash
python3 -m task_families.verification_budget_v1.generate .local/budget-source
python3 scripts/tasks.py --package .local/budget-source \
  quality x2p_queue_three_v1 .local/budget-admission
```

生成包内原有 `environment.policy_experiment` 增加 `--public-test-budget 2` 或 `6`。历史默认入口与 Policy v1 保持原样；预算条件使用 Policy 版本 2，初始 Prompt 除额度数字外相同。完整研究以冻结计划调用 [批量入口](../../scripts/verification_budget_study.py)，不要把手动改变预算后的结果混入历史条件。

生成成功不授予工业准入。首次执行新源码仍需来源匹配的质量门禁，以及两种额度的真实机制验收。后续试次仅可复用同一源码、工具链及准入身份下的完整公共前置检查；不能复用模型会话、终局奖励或上一条候选。

公开中间反馈始终由可信控制器产生。提交冻结源码并结束求解；终局奖励、保留评估及事后候选测量分别保存。增加额度不意味着控制器会替 Agent 测试、排名或回退。

## 怎样重放计划

在已配置合法 VCS/VIP、隔离 Runtime 与模型凭据的可信执行端，生成源码包并完成其准入后，可调用：

```bash
python3 scripts/verification_budget_study.py \
  --package .local/budget-source \
  --admission .local/budget-admission \
  --starts experiments/verification-budget-v1/starts \
  --inputs .local/frozen-budget-inputs \
  --plan experiments/verification-budget-v1/study-plan.json \
  --out .local/budget-replay
```

该命令会检查包、准入和输入的身份；它不会为匹配计划而更新哈希。`--inputs` 需要可信侧保存的 `r01-reward.json` 与 `r01-evaluation.json`，私有原始输入不随公开仓库发布。公开证据可用于核查结果与来源；没有原始输入时不能声称逐字重放同一实验。使用新输入或不同工具链时，应先完成相应验收并建立新的冻结计划，不与本批混合统计。

每条结束后立即保存完成记录、原始证据哈希与独立交换集合。重新调用同一命令只跳过经哈希核对的已完成试次；发现未完成试次或停止标记时拒绝自动补跑。恢复需要先检查已有证据，保留已启动试次，不因失败而替换样本。

离线汇总使用：

```bash
python3 scripts/summarize_verification_budget.py \
  .local/budget-replay .local/budget-replay-analysis.json
```

汇总区分终局奖励、保留评估、实际公开反馈与事后首候选测量，不用其中任何一项替模型选择中间版本。具体研究假设与限制见[研究报告](../../docs/verification-budget-study.md)。
