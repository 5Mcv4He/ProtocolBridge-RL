# 公开验证预算与修复候选选择

本目录保存一次预先声明的小规模对照研究。固定同一三深度队列任务、三个错误起点、综合工程工具和 20 次总动作，仅将公开 test 上限设为 2 或 6。研究问题是额外机会是否被实际使用，以及候选修改、测试和最终选择之间有什么可核查关系。

先读[研究报告](../../docs/verification-budget-study.md)理解设计与限制，再按需要核查以下证据：

| 要核查的问题 | 证据 |
| --- | --- |
| 最终实际执行及分层结果 | [12 条结果](study-results.json)、[成本与行为](cost-and-behavior.json) |
| 条件是否按计划执行 | [跨试次审计](study-audit.json)、各试次源包审计及 [预算机制验收](mechanisms/summary.json) |
| 如何核查实际反馈与候选 | [逐条轨迹](trials/)、[统一交换库存](exchange-inventory.json) |
| 模型调用前决定了什么 | [冻结计划](study-plan.json)，包含起点、顺序、条件、成本上限、停止规则和事后测量范围 |
| 两组非预算提示是否相同 | [test2 提示](prompt-test2.txt)、[test6 提示](prompt-test6.txt) |
| 三个起点真的有错吗 | [起始源码](starts/)、[实际复验](qualification/summary.json)；一个历史 Agent 错误、两个受控错误 |
| 验证器和任务是否同时改变 | [功能依赖逐文件比较](functional-dependencies.json)、[包清单](family-manifest.json) |
| 新源码是否重新验收 | [工业准入](quality/result.json)、[冻结来源](quality/freeze.json) |

完整原始交互、候选、输入与工具日志保存在可信研究存储。公开交付采用字段白名单及内容哈希，保留实际送达的工具反馈、候选演变与失败，不上传商业工具输出、私有向量或个人部署信息。终局训练奖励、独立保留评估与事后候选测量分别保存；导出成功不等于已经证明训练收益。

复现入口见[预算环境说明](../../task_families/verification_budget_v1/README.md)。重新调用模型会产生独立随机试次，不能保证复制原输出；要逐字核查原试次，应使用冻结来源和已保留证据。
