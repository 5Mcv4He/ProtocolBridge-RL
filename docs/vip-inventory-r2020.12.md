# VIP 能力范围与接入状态

本页只列项目实际依赖及潜在扩展的技术边界。个人机器上的安装包清单不等于可运行的验证能力，也不构成本项目的任务集合。

| 范围 | 当前项目状态 | 可检查的证据 |
| --- | --- | --- |
| AXI4-Lite → APB4 | Task001–004 已接入主动 AXI/APB VIP、独立 UVM Scoreboard、时序检查与程序化奖励 | [任务目录](task-catalog.md)、各任务质量门禁与研究报告 |
| AW/W 独立握手、等待、背压、错误和复位 | 已进入现有任务规格和真实验证 | [验证计划](verification-plan.md)、任务 Spec |
| 多 APB 目标路由 | Task002 已验收 | [Task002 报告](task002-evaluation-report.md) |
| 有限请求队列与执行/响应解耦 | Task003/004 已验收，模型试次仍暴露设计困难 | [Task003 报告](task003-evaluation-report.md)、[Task004 报告](task004-evaluation-report.md) |
| 完整 AXI4 Burst、ID、拆分与跨 ID 顺序 | 不能由所用 VIP 产品名推断为已实现任务；当前尚未形成验收通过的任务契约 | 新 Spec、跨协议事务配对和正反对照仍待建立 |
| UART 8N1／8E1 固定速率发送 | 已有自建 DUT、VIP 接收 Monitor、独立周期判据、正反对照及真实模型试次；当前评分器修订 4 | [任务使用入口](tasks/README.md)、[漏检与分类修正证据](verification-resources-tasks.md) |
| AMBA 测试激励生成 | 同一份结构化事务运行合法／错误桥，由固定 UVM Scoreboard 判定；不是新增协议 | [mapping](tasks/x2p_stimulus_mapping_v1.md)、[timing](tasks/x2p_stimulus_timing_v1.md) |
| 其他尚未任务化的协议 | 厂商例程或安装状态不等于正式任务验收 | [最新批次核查与选题依据](verification-resources-tasks.md)；仍需独立对象、判据和错误对照 |

对应实验使用 AMBA 或 UART VIP R-2020.12，具体 VCS、UVM、Python 和 Harness 版本保存在各批次 metadata/freeze 中。不同实验的工具链身份不能互相替代，版本及能力解释见[工具链说明](toolchain.md)。

新增协议或任务必须通过[Task Quality Gate](task-quality-gate.md)：明确 Spec，合法参考实际通过，错误变体实际被检出，独立检查事务语义及完成账目，确认 Reward 分类与信息边界，再进入真实 Agent 评测。

历史资源清点只提供文件存在和可解析性的元数据，未证明其中所有产品可仿真或适合 RL 任务。[历史审计的证据边界](vip-audit-2026-11-24.md)继续保留；不把资源数量当成已支持的任务数量。安装目录、介质检查、授权和运维记录留在可信本地存储，不列入公开能力交付。
