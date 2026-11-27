# UART 8E1：增加偶校验的完整帧

在固定速率发送中正确处理校验位。相比 8N1，这个契约增加的是数据相关的偶校验和一位更长的占用时间，不是仅换一组测试字节。

[返回任务目录](../task-catalog.md) · [共同运行与权限](README.md) · [完整 Spec](../../tasks/uart_tx_8e1_v1/spec.md)

## 要实现或触发的工程行为

每帧包含起始位、最低位先发的八个数据位、一位偶校验和停止位。校验位等于八个数据位的异或，使合计的 1 数为偶数。每位 16 周期，11 位帧共 176 周期；busy 期间不得重新装载或排队。

例如数据 0x01 具有一个 1，因此校验位必须是 1；0x03 则为 0。ready 只有在停止位保持完毕后才恢复，不能用停止位本身的值提前结束发送。低有效同步复位只要求发生在空闲阶段。

## 提交什么，怎样判定

只修改 `uart_tx.sv`。初始材料见[工作文件](../../tasks/uart_tx_8e1_v1/workspace/uart_tx.sv)，不可修改 Spec、参考、检查器或评分输入。RTL 必须自包含并保持契约接口；宏、include、外部模块、文件访问等限制见 Spec。

工业接收 Monitor 与独立周期模型共同检查字节、校验、时长、ready 及事务账目。当前评分器修订 4 检查端口交付与编译分类；旧版本的 PASS 不自动升级为当前证据。

完整必要验收通过为 1；确定的功能错误或有效候选的编译错误为 0；空／非法交付、工具故障、超时或不完整验收为 null，并分别归因。 终局奖励与独立保留评估分别记录；保留结果不回流求解。有限错误库或有限仿真不构成任意缺陷完备性证明，参考等价也只对明确比较语义成立。

## 从一份新工作区开始

以下是研究者的人工复现命令，需要[对应工具与本地配置](../toolchain.md)，输出目录应尚不存在。`test` 不会替你修改文件；先编辑指定交付物再测试。

```bash
python3 -m environment.artifact_task reset uart_tx_8e1_v1 .local/8e1-work
# 编辑 .local/8e1-work/uart_tx.sv
python3 -m environment.artifact_task test uart_tx_8e1_v1 .local/8e1-work .local/8e1-public
python3 -m environment.artifact_task submit uart_tx_8e1_v1 .local/8e1-work .local/8e1-submit
```

需要带依赖清单的材料包时，使用 `python3 -m verification_resources.production produce uart-transmit 8e1 .local/8e1-package`，再按[共同说明](README.md)核对和初始化。人工 CLI 的完整研究输出不应直接作为 Agent 工具反馈；真实试次由受控运行器投影反馈并执行预算。

## 已有什么证据，仍不能说明什么

[当前准入检查](../../experiments/verification-resources-v1/uart-quality-v4.json)覆盖该族的合法与错误对照；[评分实现](../../verifier/uart_tx/campaign_v4.py)可核查判定机制。[研究报告](../verification-resources-tasks.md)分别列出各次真实模型试验、实际修复、失败与版本变化；[逐试次结果](../../experiments/verification-resources-v1/study-results-current.json)保留真实分母。

本页是冻结包外的使用指南，不改变原任务或准入身份。小样本与不同版本的结果不能合并为稳定成功率，也尚未证明模型参数训练收益。
