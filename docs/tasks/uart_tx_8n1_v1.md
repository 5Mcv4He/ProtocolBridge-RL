# UART 8N1：保存字节并完成串行帧

把接受的并行字节转换成准确的串行帧。这个任务考察输入锁存、位顺序、位时间与 ready 的完整生命周期，不要求实现接收器或寄存器总线。

[返回任务目录](../task-catalog.md) · [共同运行与权限](README.md) · [完整 Spec](../../tasks/uart_tx_8n1_v1/spec.md)

## 要实现或触发的工程行为

每帧为起始位、最低位先发的八个数据位、停止位，共 10 位。每位保持 16 个时钟周期，帧共 160 周期。只有 valid 与 ready 同时为 1 的沿才能接受；busy 期间的新 valid/data 必须被忽略，不能覆盖当前字节或排队。

例如接受 0x01 后，数据部分先发 1、再发七个 0。即使发送中 data 改成 0xFF，当前帧也必须仍表示 0x01。复位低有效且同步；本契约只要求空闲复位，不包含事务中取消。

## 提交什么，怎样判定

只修改 `uart_tx.sv`。初始材料见[工作文件](../../tasks/uart_tx_8n1_v1/workspace/uart_tx.sv)，不可修改 Spec、参考、检查器或评分输入。RTL 必须自包含并保持契约接口；宏、include、外部模块、文件访问等限制见 Spec。

UART VIP 接收 Monitor 解码帧；独立周期模型同时检查 ready、位值、位长及接受／完成账目。当前采用评分器修订 5；原修订的漏检和误分类记录保留，不能复用旧准入。

完整必要验收通过为 1；确定的功能错误或有效候选的编译错误为 0；空／非法交付、工具故障、超时或不完整验收为 null，并分别归因。 终局奖励与独立保留评估分别记录；保留结果不回流求解。有限错误库或有限仿真不构成任意缺陷完备性证明，参考等价也只对明确比较语义成立。

## 从一份新工作区开始

以下是研究者的人工复现命令，需要[对应工具与本地配置](../toolchain.md)，输出目录应尚不存在。`test` 不会替你修改文件；先编辑指定交付物再测试。

```bash
python3 -m environment.artifact_task reset uart_tx_8n1_v1 .local/8n1-work
# 编辑 .local/8n1-work/uart_tx.sv
python3 -m environment.artifact_task test uart_tx_8n1_v1 .local/8n1-work .local/8n1-public
python3 -m environment.artifact_task submit uart_tx_8n1_v1 .local/8n1-work .local/8n1-submit
```

需要带依赖清单的材料包时，使用 `python3 -m verification_resources.production_v3 produce uart-transmit 8n1 .local/8n1-package`，再按[共同说明](README.md)核对和初始化。人工 CLI 的完整研究输出不应直接作为 Agent 工具反馈；真实试次由受控运行器投影反馈并执行预算。

## 已有什么证据，仍不能说明什么

[当前准入检查](../../experiments/task-production-v2/uart-quality-v5.json)覆盖该族的合法与错误对照；[评分实现](../../verifier/uart_tx/campaign_v5.py)可核查判定机制。[研究报告](../verification-resources-tasks.md)分别列出各次真实模型试验、实际修复、失败与版本变化；[逐试次结果](../../experiments/verification-resources-v1/study-results-current.json)保留真实分母。

本页是冻结包外的使用指南，不改变原任务或准入身份。小样本与不同版本的结果不能合并为稳定成功率，也尚未证明模型参数训练收益。
