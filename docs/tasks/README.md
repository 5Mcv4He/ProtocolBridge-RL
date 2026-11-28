# 有限工程任务：选择、执行与核查

这组任务复用同一个受控交付流程，但测量串行实现、测试构造、检查器设计及不同同步状态修复。先选择要测量的能力，再按对应指南理解交付物与判据；不要因都叫 test，就认为它们执行同一种检查。

| 任务指南 | 唯一可修改交付物 | 材料包选择 |
| --- | --- | --- |
| [UART 8N1](uart_tx_8n1_v1.md) | `uart_tx.sv` | `uart-transmit` / `8n1` |
| [UART 8E1](uart_tx_8e1_v1.md) | `uart_tx.sv` | `uart-transmit` / `8e1` |
| [回绕累加器](accumulator_wrap_repair_v1.md) | `accumulator.sv` | `reference-repair` / `wrap` |
| [饱和累加器](accumulator_saturating_repair_v1.md) | `accumulator.sv` | `reference-repair` / `saturating` |
| [映射类测试生成](x2p_stimulus_mapping_v1.md) | `stimulus.json` | `stimulus-design` / `mapping` |
| [时序类测试生成](x2p_stimulus_timing_v1.md) | `stimulus.json` | `stimulus-design` / `timing` |
| [FIFO 深度 2](../../tasks/fifo_checker_d2_v1/README.md) | `checker.sv` | `fifo-checker` / `depth2` |
| [FIFO 深度 3](../../tasks/fifo_checker_d3_v1/README.md) | `checker.sv` | `fifo-checker` / `depth3` |
| [硬件置位优先](../../tasks/status_set_dominant_repair_v1/README.md) | `status_register.sv` | `status-register` / `set-dominant` |
| [软件清除优先](../../tasks/status_clear_dominant_repair_v1/README.md) | `status_register.sv` | `status-register` / `clear-dominant` |
| [I²C 字节交付](i2c-write-sink.md) | `i2c_sink.sv` | `i2c-write-sink` / `byte` |
| [I²C 事务内组字](i2c-write-sink.md) | `i2c_sink.sv` | `i2c-write-sink` / `word` |
| [FIFO 深度 1／5](fifo-checker-expanded.md) | `checker.sv` | `fifo-checker-expanded` / `depth1`、`depth5` |
| [RFFE RW／W1C 寄存器](rffe-register.md) | `rffe_register.sv` | `rffe-register` / `rw`、`w1c` |
| [置位计数／末尾零综合修复](bitfold-synthesis-repair.md) | `bitfold.sv` | `bitfold-synthesis` / `population`、`trailing-zero` |
| [I²C 字节／组字骨架补全](i2c-completion.md) | `i2c_sink.sv` | `i2c-completion` / `byte`、`word` |
| [SWD有限读响应](../swd-read-evaluation.md) | `target.sv` | production_v7：`dp0-latched` |
| [寄存器RW／W1C检查器](../register-checker-evaluation.md) | `checker.sv` | production_v6：`rw`、`w1c` |

[全项目任务目录](../task-catalog.md)包含另 11 个 X2P 契约；这里二十三个有限任务身份对应[追加 Registry（含原目录）](../../tasks/artifact-registry-v3.json)。其中两个 I²C 补全起点复用已有功能契约，不计作新增协议能力。指南放在冻结任务目录之外，不改变材料包的完整文件清单。

## Agent 能看到什么

已发布有限交付试次开放 **read、edit、test、submit**，最多 20 次动作、4 次公开测试。read 只能读取本试次 Spec 与交付文件，edit 只能替换交付物；模型没有任意 shell、可信参考或评分源码读取工具。test 反馈经过控制器投影，绑定当前内容 SHA-256，旧版本 PASS 不能代表新编辑已通过。

submit 冻结交付并结束求解，再运行终局与独立保留评估；私有结果不送回继续修改。终局 Reward、保留评估、事后分析分别保存。X2P 的九动作综合工具不自动适用于这些任务；历史边界见[原Session](../../environment/artifact_task/session_v3.py)与[文本动作研究](../verification-resources-tasks.md)；新四动作原生接口及隔离边界见[实际验收](../native-tool-delivery-evaluation.md)，寄存器检查器使用[run_v4](../../environment/native_tools/run_v4.py)。

## 人工复现与材料包生产

各任务指南提供 reset/test/submit 命令。它们是可信研究者使用的 CLI，**不是绕过 Agent 权限和预算的模型工具**。提交目录保存冻结交付、terminal.json 和 reserved-evaluation.json；分别阅读终局与保留结果，不把两个分数相加。无效提交和工具故障均可为 null，但归因必须分别检查。

生产一份带来源清单的材料包，例如 UART 偶校验实例：

```bash
python3 -m verification_resources.production_v5 produce uart-transmit 8e1 .local/uart-package
python3 -m verification_resources.production_v5 check .local/uart-package
python3 -m verification_resources.production_v5 reset .local/uart-package .local/uart-work
```

生产前核对有效准入与源码，check 核对包内容与共享依赖，reset 才复制初始材料。**这些步骤不执行新的 RTL 验收，也不启动模型。** 使用与清单匹配的 checkout 和[工具配置](../toolchain.md)才能继续实际 test/submit；不能通过改写旧哈希复用失效准入。UART 当前要求 verifier revision 5，Checker 深度 2／3 为 revision 2、深度 1／5 为 revision 3；其他有限功能评分版本见 Registry；I²C 生成器与质量门禁为修订 2、功能评分为修订 1。生产器要求完整依赖集合精确匹配，不再仅遍历清单中已有条目。

## 如何追溯一次真实求解

[预声明计划与证据索引](../../experiments/verification-resources-v1/README.md)连接实际执行条件、当前准入、同源码漏检复验与六批共 14 条模型记录；[研究报告](../verification-resources-tasks.md)解释有效编辑、修复、格式拒绝和可信分类器故障。它们包含不同验证版本，不作为一个共同成功率。

[版本化轨迹交换](../task-rollout-exchange.md)保留实际送达反馈、候选、奖励和来源。导出成功不等于已证明适合训练；未获得的 Token IDs、行为概率与权重版本仍不可用。公开源码可能被模型预训练接触，运行时隔离不等于长期题库保密。

新增四份契约的[生产与研究报告](../task-production-stage-v2.md)连接 36／39 项实际门禁、四条真实轨迹和反例发现。通用人工命令仍是 `python3 -m environment.artifact_task reset/test/submit TASK ...`；Task ID 以相应 task.json 为准。[本阶段证据入口](../../experiments/task-production-v2/README.md)不与旧六批合并计算成功率。

[I²C 生产与求解研究](../i2c-sink-evaluation.md)新增两个契约及两条预声明轨迹，记录一次最终成功修复和一次已知失败提交。该阶段材料化 v7 核对十二份包及完整 Registry 依赖；历史材料化与运行条件保持原版本。

[多验证资源阶段](../task-production-stage-v3.md)新增八个任务身份并分别完成工业门禁。运行器修订 10／Session 4 对反馈类别与奖励一致性采用保守过滤，并记录综合错误类别；历史运行器不变。实际机制验收、材料化与新模型校准状态以该报告为准。

最新 [多资源分层校准](../task-production-stage-v3.md)新增四条主试次和一条独立反馈版本试次：两条终局成功、两条未编辑失败提交、后续一条未提交。按任务与条件分别阅读，不将全部任务入口视为已经得到稳定难度校准。

## 寄存器事件检查器

[RW与W1C检查器](../register-checker-evaluation.md)要求交付判断读回是否正确的状态模型。候选检查器由独立事件判据评价，既检查漏报也检查误报；不继承串行VIP的准入。两份新包及真实模型记录使有限任务身份达到22个，新版[CLI与复现入口](../../experiments/register-checker-v1/README.md)保留此前接口。

## SWD有限读响应

[研究报告](../swd-read-evaluation.md)解释双向驱动权、请求捕获和独立引脚判据；[复现入口](../../experiments/swd-read-v1/README.md)使用cli_v3与run_v5。SWD阶段共有23个有限身份，新入口不改变旧任务的源码准入。

## 功能保持与结构预算

[结构优化任务](../bitfold-optimization-evaluation.md)以功能正确但超额的位计数实现为起点。[复现入口](../../experiments/bitfold-optimization-v1/README.md)使用cli_v4、production_v8与run_v6；当前有限身份为24个。测量只在完整功能通过后反馈，不改变此前任务条件。
