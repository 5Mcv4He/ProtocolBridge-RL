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

[预算研究时的交换库存](../experiments/verification-budget-v1/exchange-inventory.json)引用并保留历史清单：107 条研究记录中 67 条具备完整工具轨迹。预算研究新增 12 条真实试次，全部经源包审计后导出，不新增交换 Schema，也不重写历史 v1–v5。

本轮有三条未 submit 的完整交互轨迹，终局记录为 `agent_incomplete`、Reward=null，保留评估未运行；没有用最后一次编辑伪造提交或补评 0。`candidate-decisions.json` 是另外的离线版本关系分析，`tool-summary.json` 是供人阅读的实际事件投影，均不冒充模型收到的新反馈。核查模型实际可见内容应回到 v5 工具事件、送达标记和源码制品。[预算研究](verification-budget-study.md)进一步解释实际测试、最终版本和事后测量的区别。

## 有限工程交付的 v6 适配

UART RTL、结构化测试事务和独立参考修复使用 [v6 导出器](../scripts/artifact_exchange.py)。它重放原始模型响应的单动作解析与 Session，核对实际送达反馈、候选内容、预算、提交冻结及来源计划，再导出相同的 training / evaluation / analysis / artifacts 职责分区。无效动作完整保留，不自动拆分或补写编辑。

[四个审计负例](../experiments/verification-resources-v1/audit-negative-checks-v2.json)实际篡改了反馈字段、送达内容、提交源码及停止确认，均被拒绝。这里的审计只验证记录一致性与信息边界，不为有缺陷的验证器背书：UART 旧版漏检对应的轨迹仍保留，当前用途状态由[研究库存](../experiments/verification-resources-v1/exchange-inventory.json)另外标明。

```bash
python3 -m scripts.artifact_exchange NEW_EXCHANGE RAW_TRIAL_1 RAW_TRIAL_2
python3 -m scripts.analyze_artifact_study NEW_ANALYSIS.json RAW_TRIAL_1 RAW_TRIAL_2
```

需要原始本地交互记录，公开摘要不能代替重放输入。v6 中的公开制品不是原始采样数据，仍缺 Token IDs、行为概率和精确模型权重；终局奖励与独立评估分离，事后测量不写回模型观察。各版本保留历史用途，不能自动把所有导出记录当成当前训练候选。

对于在可信分类器故障后中断的试次，v6 保留实际动作和已送达反馈，明确 `solver_stop_confirmed=false`、未执行终局与保留评分。审计不把未知的停止状态改为成功；只有确认没有越界评分后，才允许作为不完整研究记录导出。
