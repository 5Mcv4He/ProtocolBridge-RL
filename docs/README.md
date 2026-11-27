# 人类阅读入口

这里帮助读者从工程问题进入机制、代码和证据。当前总览以[首页](../README.md)、[任务目录](task-catalog.md)与[交换库存](../experiments/i2c-sink-v1/exchange-inventory.json)为准；研究报告中的“当前”属于各自冻结阶段。历史结果不因新功能出现而改写。

## 先理解系统，再选择任务

| 想了解什么 | 阅读入口 |
| --- | --- |
| 项目为什么做、完成到哪里 | [项目首页](../README.md)、[最新 I²C 任务与真实修复](i2c-sink-evaluation.md) |
| Task、Environment、Verifier 和 Reward 怎样协作 | [架构总览与 001 Scoreboard 实例](architecture.md) |
| 选哪个任务、使用哪条执行路径 | [任务目录](task-catalog.md)、[十二个有限工程契约指南](tasks/README.md) |
| 工具能判断什么，尚不能证明什么 | [工具与证据层次](toolchain.md)、[VIP 接入范围](vip-inventory-r2020.12.md) |
| 怎样交付并审计真实求解轨迹 | [当前 v5–v7 入口](task-rollout-exchange.md)、[早期契约演进](rollout-data-contract.md) |

[最新 I²C 研究](i2c-sink-evaluation.md)连接串行时序、事务边界、被拒绝的生成版本、实际修复和成本；[此前 Checker 与状态寄存器研究](task-production-stage-v2.md)保留各自冻结范围。

## 从工程契约到可靠任务

| 工程问题 | 方法与证据 |
| --- | --- |
| 怎样判定一个任务可以进入模型评测 | [任务质量门禁](task-quality-gate.md) |
| 地址窗口变化会引入哪些验证义务 | [路由族生产](task-family-production.md)、[漏检与校准](router-family-evaluation.md)、[生成器入口](../task_families/router_v1/README.md) |
| 容量变化怎样影响回绕与退休账目 | [队列族生产](queue-family-production.md)、[实际验收与模型研究](queue-family-evaluation.md)、[生成器入口](../task_families/queue_v1/README.md) |
| 路由与排队组合会新增什么风险 | [组合契约与独立检查](composed-task-production.md)、[组合阶段研究](composed-environment-evaluation.md) |
| UART、测试激励和参考修复如何分别评分 | [三类任务与同源码漏检复验](verification-resources-tasks.md)、[首轮准入及试次索引](../experiments/verification-resources-v1/README.md) |
| 检查器自己怎样接受评价，状态更新怎样独立核验 | [新生产方法与真实修复](task-production-stage-v2.md)、[当前阶段证据](../experiments/task-production-v2/README.md) |

## Agent 怎样利用工具和反馈

| 研究问题 | 接口与实际结果 |
| --- | --- |
| 可以看到什么、获得什么测试反馈 | [Observation / Feedback Policy](observation-policy.md)、[原 Policy 实验](policy-evaluation-report.md) |
| 编译与需求级诊断是否帮助修复 | [受控工程工具](engineering-tools.md)、[配对修复研究](engineering-tools-evaluation.md) |
| 怎样观察握手并构造局部实验 | [运行时实验](runtime-experiments.md)、[事件导航 v2](runtime-events-v2.md)、[原版实测](runtime-tools-evaluation.md) |
| 综合、自身网表等价与时序功耗分别说明什么 | [工具接口](synthesis-tools.md)、[验收与模型试次](synthesis-tools-evaluation.md) |
| 如何避免将旧候选的结果当作新版本证据 | [九动作综合环境](engineering-lab.md)、[候选回退研究](composed-environment-evaluation.md) |
| 更多测试额度是否改变最终候选选择 | [预算对照与候选演变](verification-budget-study.md)、[冻结运行入口](../task_families/verification_budget_v1/README.md) |

## 按阶段核查历史结果

这些页面保留当时的任务、工具、样本和结论范围，不是当前项目能力的总清单。001 的标准基线仍为 revision 3，旧 128 笔交付已废弃。

| 范围 | 核查入口 |
| --- | --- |
| 001 revision 3 | [任务](../tasks/axil_to_apb4_001/README.md)、[验证计划](verification-plan.md)、[评估报告](../mvp-evaluation-report.md)、[历史运行手册](mvp-running.md)、[原 Agent 工作流](agent-workflow.md) |
| 001 批量 A/C/E 与修复 | [批量研究](batch-evaluation-report.md)、[执行契约](batch-study.md)、[证据索引](../experiments/batch-study-001/README.md) |
| 002 路由 | [任务](../tasks/axil_to_apb4_router_002/README.md)、[研究报告](task002-evaluation-report.md) |
| 003 队列 | [任务](../tasks/axil_to_apb4_queue_003/README.md)、[独立生成](task003-evaluation-report.md)、[同起点修复](task003-repair-report.md) |
| 004 执行／响应解耦 | [任务](../tasks/axil_to_apb4_decoupled_004/README.md)、[研究报告](task004-evaluation-report.md) |
| 早期方法与资源 | [001–003 阶段总结](multi-task-research-report.md)、[研究设计](research-design.md)、[历史资源审计边界](vip-audit-2026-11-24.md) |

## 文档维护

创建或更新面向人类的页面时，遵循[文档设计规范](documentation-guidelines.md)；图源及视觉参考见[图形目录](diagrams/README.md)。

## 新任务或版本更新时

每个任务必须提供固定的人类入口，说明 Spec、验证计划与运行步骤。新包应在冻结前包含 README；已有冻结包若未包含，使用本目录 `tasks/` 下的指南并从任务目录链接，避免添加文件改变材料包身份；后续实测报告和证据由[统一任务目录](task-catalog.md)持续链接，历史冻结任务包不回改。不能只增加 RTL、YAML 或日志。描述该任务的对象、协议边界、典型事务图、检查与奖励、Agent 权限、可复用步骤，以及已验证／未验证／未实现的区别。

系统公共机制放本目录，任务特有内容放任务目录或上述外置指南，并相互链接。修改共同机制时同步架构／工作流／运行文档；改变 Spec 或评分规则时更新版本和报告，保留历史结果对应的冻结版本。图表用于解释真实结构，不能把计划画成已实现。
