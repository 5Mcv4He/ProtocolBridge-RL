# VIP 能力范围与接入状态

本页只列项目实际依赖及潜在扩展的技术边界。个人机器上的安装包清单不等于可运行的验证能力，也不构成本项目的任务集合。

| 范围 | 当前项目状态 | 可检查的证据 |
| --- | --- | --- |
| AXI4-Lite → APB4 | Task001–004 已接入主动 AXI/APB VIP、独立 UVM Scoreboard、时序检查与程序化奖励 | [任务目录](task-catalog.md)、各任务质量门禁与研究报告 |
| AW/W 独立握手、等待、背压、错误和复位 | 已进入现有任务规格和真实验证 | [验证计划](verification-plan.md)、任务 Spec |
| 多 APB 目标路由 | Task002 已验收 | [Task002 报告](task002-evaluation-report.md) |
| 有限请求队列与执行/响应解耦 | Task003/004 已验收，模型试次仍暴露设计困难 | [Task003 报告](task003-evaluation-report.md)、[Task004 报告](task004-evaluation-report.md) |
| 完整 AXI4 Burst、ID、拆分与跨 ID 顺序 | 不能由所用 VIP 产品名推断为已实现任务；当前尚未形成验收通过的任务契约 | 新 Spec、跨协议事务配对和正反对照仍待建立 |
| 其他 AMBA 或非 AMBA 协议 | 未纳入当前正式 Agent 评测集合 | 必须独立证明工具、任务和奖励有效性 |

现有实验使用 AMBA VIP R-2020.12，具体 VCS、UVM、Python 和 Harness 版本保存在各批次 metadata/freeze 中。不同实验的工具链身份不能互相替代，版本及能力解释见[工具链说明](toolchain.md)。

新增协议或任务必须通过[Task Quality Gate](task-quality-gate.md)：明确 Spec，合法参考实际通过，错误变体实际被检出，独立检查事务语义及完成账目，确认 Reward 分类与信息边界，再进入真实 Agent 评测。

历史资源清点只提供文件存在和可解析性的元数据，未证明其中所有产品可仿真或适合 RL 任务。[历史审计的证据边界](vip-audit-2026-11-24.md)继续保留；不把资源数量当成已支持的任务数量。安装目录、介质检查、授权和运维记录留在可信本地存储，不列入公开能力交付。
