# 人类阅读入口

本目录是理解、讲解和复用项目的固定入口。001的冻结标准基线是[001 X2P](../tasks/axil_to_apb4_001/README.md)，旧 128 笔交付已废弃。研究方向与已实现能力分开阅读。

| 问题 | 页面 |
|---|---|
| 新任务是否可靠，Task002实际测到什么 | [任务质量门禁](task-quality-gate.md)、[Task002报告](task002-evaluation-report.md)、[任务包](../tasks/axil_to_apb4_router_002/README.md) |
| 当前体系测量了什么，离训练数据还有什么差距 | [多任务研究总结](multi-task-research-report.md) |
| 多请求队列测到哪些错误 | [Task003独立生成](task003-evaluation-report.md)、[同起点修复](task003-repair-report.md)、[队列任务包](../tasks/axil_to_apb4_queue_003/README.md) |
| 怎样选择任务、复用环境和交付轨迹 | [统一任务入口](task-catalog.md)、[轨迹交换与边界](rollout-data-contract.md) |
| 项目有什么、当前完成到哪里 | [仓库首页](../README.md)、[实测报告](../mvp-evaluation-report.md) |
| Task、环境、验证器、评分器分别是什么 | [架构与 Scoreboard](architecture.md) |
| DSH 在哪里，Agent 能看什么，怎样生成 Reward | [Agent 工作流](agent-workflow.md) |
| A／C／E 可见信息与反馈怎样配置、冻结和对照 | [Observation / Feedback Policy](observation-policy.md) |
| 真实 Policy 实验结果、失败轨迹和统计结论边界 | [Policy 实验报告](policy-evaluation-report.md)、[证据索引](../experiments/policy-v1/README.md) |
| 批量成功率、真实反馈利用、格式失败和配对修复 | [批量实验报告](batch-evaluation-report.md)、[执行契约](batch-study.md)、[证据索引](../experiments/batch-study-001/README.md) |
| 定向／边界／随机／复位怎样验证，覆盖是否充分 | [验证计划与缺口](verification-plan.md) |
| 怎样安装、reset/test/submit、重放和重新调用模型 | [运行手册](mvp-running.md) |
| OS 隔离、综合、形式验证是什么，还缺什么 | [工具与能力边界](toolchain.md) |
| RTL 的精确契约 | [任务 001 Spec](../tasks/axil_to_apb4_001/spec.md) |

## 新任务或版本更新时

每个任务包必须提供一个 README 作为人类入口，说明 Spec、验证计划与运行步骤；后续实测报告和证据由[统一任务目录](task-catalog.md)持续链接，历史冻结任务包不回改。不能只增加 RTL、YAML 或日志。描述该任务的对象、协议边界、典型事务图、检查与奖励、Agent 权限、可复用步骤，以及已验证／未验证／未实现的区别。

系统公共机制放本目录，任务特有内容放任务目录并相互链接。修改共同机制时同步架构／工作流／运行文档；改变 Spec 或评分规则时更新版本和报告，保留历史结果对应的冻结版本。图表用于解释真实结构，不能把计划画成已实现。

## 历史研究

[研究设计](research-design.md)、[VIP 盘点](vip-inventory-r2020.12.md)、[早期审计](vip-audit-2026-11-24.md)保留当时背景，不作为当前功能验收来源。
