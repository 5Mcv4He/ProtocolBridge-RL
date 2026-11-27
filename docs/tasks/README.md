# 六个有限工程契约：选择、执行与核查

这组任务复用同一个受控交付流程，但测量三种不同工作：实现串行行为、构造有效测试、修复同步状态转移。先选择要测量的能力，再按对应指南理解交付物与判据；不要因都叫 test，就认为它们执行同一种检查。

| 任务指南 | 唯一可修改交付物 | 材料包选择 |
| --- | --- | --- |
| [UART 8N1](uart_tx_8n1_v1.md) | `uart_tx.sv` | `uart-transmit` / `8n1` |
| [UART 8E1](uart_tx_8e1_v1.md) | `uart_tx.sv` | `uart-transmit` / `8e1` |
| [回绕累加器](accumulator_wrap_repair_v1.md) | `accumulator.sv` | `reference-repair` / `wrap` |
| [饱和累加器](accumulator_saturating_repair_v1.md) | `accumulator.sv` | `reference-repair` / `saturating` |
| [映射类测试生成](x2p_stimulus_mapping_v1.md) | `stimulus.json` | `stimulus-design` / `mapping` |
| [时序类测试生成](x2p_stimulus_timing_v1.md) | `stimulus.json` | `stimulus-design` / `timing` |

[全项目任务目录](../task-catalog.md)包含另 11 个 X2P 契约；这里六份指南对应[有限交付 Registry](../../tasks/artifact-registry.json)。指南放在冻结任务目录之外，不改变材料包的完整文件清单。

## Agent 能看到什么

已发布有限交付试次开放 **read、edit、test、submit**，最多 20 次动作、4 次公开测试。read 只能读取本试次 Spec 与交付文件，edit 只能替换交付物；模型没有任意 shell、可信参考或评分源码读取工具。test 反馈经过控制器投影，绑定当前内容 SHA-256，旧版本 PASS 不能代表新编辑已通过。

submit 冻结交付并结束求解，再运行终局与独立保留评估；私有结果不送回继续修改。终局 Reward、保留评估、事后分析分别保存。X2P 的九动作综合工具不自动适用于这些任务；真实边界见[session](../../environment/artifact_task/session_v2.py)、[当前运行器](../../environment/artifact_task/runner_v5.py)与[反馈及模型研究](../verification-resources-tasks.md)。

## 人工复现与材料包生产

各任务指南提供 reset/test/submit 命令。它们是可信研究者使用的 CLI，**不是绕过 Agent 权限和预算的模型工具**。提交目录保存冻结交付、terminal.json 和 reserved-evaluation.json；分别阅读终局与保留结果，不把两个分数相加。无效提交和工具故障均可为 null，但归因必须分别检查。

生产一份带来源清单的材料包，例如 UART 偶校验实例：

```bash
python3 -m verification_resources.production produce uart-transmit 8e1 .local/uart-package
python3 -m verification_resources.production check .local/uart-package
python3 -m verification_resources.production reset .local/uart-package .local/uart-work
```

生产前核对有效准入与源码，check 核对包内容与共享依赖，reset 才复制初始材料。**这些步骤不执行新的 RTL 验收，也不启动模型。** 使用与清单匹配的 checkout 和[工具配置](../toolchain.md)才能继续实际 test/submit；不能通过改写旧哈希复用失效准入。UART 当前要求 verifier revision 4，其余两类为 revision 1。

## 如何追溯一次真实求解

[预声明计划与证据索引](../../experiments/verification-resources-v1/README.md)连接实际执行条件、当前准入、同源码漏检复验与六批共 14 条模型记录；[研究报告](../verification-resources-tasks.md)解释有效编辑、修复、格式拒绝和可信分类器故障。它们包含不同验证版本，不作为一个共同成功率。

[统一 v6 交换](../task-rollout-exchange.md)保留实际送达反馈、候选、奖励和来源。导出成功不等于已证明适合训练；未获得的 Token IDs、行为概率与权重版本仍不可用。公开源码可能被模型预训练接触，运行时隔离不等于长期题库保密。
