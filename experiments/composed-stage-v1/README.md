# 组合任务与综合工具：证据入口

本阶段把多目标地址路由与有限请求队列组合为一个新任务，并研究工具如何帮助 Agent 修复真实时序错误。最重要的结果不是任务数量增加，而是发现了一个能够通过原门禁的复位缺陷，以及一条放弃公开可通过中间候选的真实轨迹。[研究报告](../../docs/composed-environment-evaluation.md)解释机制、对照条件和结论边界。

## 先看哪些证据

| 要核查的问题 | 实际结果及入口 |
| --- | --- |
| 新任务是否经过工业验收？ | [修订 2 准入](composed-v2/summary.json)：2 种参考、完整 25／公开 23 case、19 个错误对照、48 个必要覆盖点及 40 项机制检查 |
| 为什么需要修订？ | [同源码漏检复验](reset-target-gap/summary.json)：原完整验证 PASS，目标 2 复位场景 FAIL，合法参考 PASS |
| 综合工具是否实际运行？ | [九动作联用验收](tools/combined-acceptance.json)通过 17 项检查；[运行时](tools/runtime-acceptance.json)29 项及[综合](tools/synthesis-acceptance.json)20 项检查另列 |
| 模型表现如何？ | [三条预定试次](study-plan.json)全部完成：[结果](study-results.json)均有效提交、终局及保留奖励均为 0，协议错误为 0 |
| 是否出现有效的局部修复？ | [中间候选事后公开测试](analysis/intermediate-public.json)21/21 PASS；求解时未曝光、未做私有评分，不替换最终 Reward=0 |
| 最终输入是否有效？ | [组合任务精确输入资格检查](analysis/composed-input-qualification.json)：合法参考在实际冻结的奖励及保留输入上分别 25/25 PASS |
| 生产成本与复用空间怎样？ | [准入成本](admission-costs.json)、[源码重复测量](final-source-footprint.json)、[确定性重建](reproduction.json)分别回答执行开销、存储重复与来源一致性 |

每个条件只有一次模型试次，不能形成稳定成功率或工具收益结论。三条共使用 SDK 报告的 214,795 Token；货币费用不可取得。更详细的反馈被实际查询，却没有形成最终成功修复。

## 轨迹与不同用途的数据

[综合修复](repair-combined/exchange/manifest.json)、[基础诊断修复](repair-diagnostic/exchange/manifest.json)和[组合任务独立求解](composed-rollout/exchange/manifest.json)各包含候选源码、实际送达的工具反馈、最终提交及审计结果。每份交换的 `training/`、`evaluation/`、`analysis/` 分别承载终局训练记录、保留评估和事后测量；后两者不能伪装成求解时的观察。

[历史路由轨迹](historical-router-exchange/manifest.json)首次纳入统一 v5 交换，但不是新增模型试次。[交换库存](exchange-inventory.json)给出 v2–v5 共 95 条研究交换记录、55 条具备完整工具轨迹的计数依据；不同条件不合并计算成功率，也不保证这些记录适合任意训练算法。[任务库存](task-inventory.json)区分 11 个 Task ID 的来源、准入和模型测量状态。综合环境升级仍属于原队列任务，不另算一个 Task。

## 历史保留与复现边界

`composed/` 保存已被后续漏检实验推翻充分性的初版准入；[说明](composed/qualification-note.json)指向当前 `composed-v2/`。可信验证器开发中的误判与不可判定结果保留在[连接／复位修正](verification-corrections.json)及[检查器执行计数修正](reset-liveness-correction.json)中，不能归入模型 RTL 失败。没有改写原 Task001–004 或历史任务族证据。

复现从[任务生产说明](../../docs/composed-task-production.md)、[综合工程环境](../../docs/engineering-lab.md)及[统一导出入口](../../docs/task-rollout-exchange.md)开始。实际仿真需要独立配置合法 VCS、AMBA VIP 与 UVM；源码重建和哈希检查本身不执行 RTL 验证。公开记录不包含商业软件、私有向量、个人部署或重复原始日志。完整原始轨迹留在可信研究存储，公开清单用于核对本次筛选后的交付文件。
