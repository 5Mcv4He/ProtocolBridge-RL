# 从任务包到可核查的轨迹交付

相同的任务名称不足以确定一条轨迹的含义：Spec、验证器、公开工具和反馈版本都可能不同。统一导出入口先确认**产生轨迹的源码与所提供的任务包一致**，再使用该包自己的审计逻辑，核对模型当时真正收到的反馈。

```bash
python3 scripts/export_task_rollouts.py \
  --package SOURCE_MATCHED_PACKAGE \
  --experiment COMPLETE_RAW_COHORT \
  --out NEW_EXCHANGE_DIRECTORY
```

这里只接受受信任的项目任务包，不是加载任意第三方插件的安全边界。需要完整本地原始证据；已经筛选过的 GitHub 摘要通常不足以重新执行完整轨迹审计。

入口检查包清单、Task ID 和执行依赖哈希。v5 输出使用统一的任务及事件记录，同时保留原审计器、源实验、导出器和任务包的哈希。生成包内记录的 Git commit 可能是生成时建立的本地身份，并非公开仓库中的可直接检出提交；复现应使用公开生产器、固定基础提交和完整包清单核对源码。[重建核对](../experiments/composed-stage-v1/reproduction.json)检查的是这些文件与生产器哈希。旧 v1–v4 交付不被重写。将同一条历史轨迹转换为 v5 不会增加模型试次数。

| 输出 | 内容与用途 |
| --- | --- |
| `training/rollouts.jsonl` | 实际工具动作、送达标记、允许的反馈、最终提交和终局 Reward |
| `evaluation/heldout.jsonl` | 独立保留评估；不能替换或回流为训练奖励 |
| `analysis/offline.jsonl` | 事后首候选测量及包含评估开销的整条运行成本 |
| `artifacts/` | 按内容哈希引用的 Prompt、可见文件内容和候选源码 |
| `source-binding.json` | 实际执行、任务包、审计器与导出清单之间的来源绑定 |

综合工具轨迹还保留候选版本绑定、compile/inspect/synth/experiment/observe 次数及可取得的工具耗时。没有取得的 API 费用、Token IDs、行为 log probability 和模型权重版本继续标记为不可用；这些记录不是无损的 on-policy 训练样本，也没有据此进行模型参数训练。

“研究中存在一条试次”“原始证据足以审计”“已经形成交换记录”与“适合具体训练算法”是四个不同判断。不能将轨迹导出成功直接表述为已经得到有效训练收益。

实现：[统一入口](../scripts/export_task_rollouts.py) · [v5 导出器](../scripts/rollout_exchange_v5.py)。Task 的执行与准入继续使用[任务目录入口](task-catalog.md)。

[当前交换库存](../experiments/composed-stage-v1/exchange-inventory.json)保留分版本计数及文件哈希核查依据：95 条记录中 55 条具备完整工具轨迹。本轮新增 3 条模型试次，另有 1 条历史路由轨迹首次导出；后者不增加研究样本数。
