# 回绕累加器：优先级与有限位宽状态更新

修复一个保存 8 位状态的同步模块。任务把状态更新优先级与模运算分开定义，再用独立参考检查所有允许的状态转移，避免只通过几个仿真样例。

[返回任务目录](../task-catalog.md) · [共同运行与权限](README.md) · [完整 Spec](../../tasks/accumulator_wrap_repair_v1/spec.md)

## 要实现或触发的工程行为

上升沿更新，优先级为低有效同步复位、load 装载、enable 累加、否则保持。加法丢弃第九位进位，采用模 256 回绕；load 与 enable 同时有效是合法输入，必须执行装载。

例如 q=250、value=10 时累加得到 4；若 load 同时为 1，应得到 10。比较使用二态同步 RTL 语义，不以“必须先复位”排除任意当前状态，也不容忍额外流水线延迟。

## 提交什么，怎样判定

只修改 `accumulator.sv`。初始材料见[工作文件](../../tasks/accumulator_wrap_repair_v1/workspace/accumulator.sv)，不可修改 Spec、参考、检查器或评分输入。RTL 必须自包含并保持契约接口；宏、include、外部模块、文件访问等限制见 Spec。

Formality 比较候选与经审查的独立参考 RTL。参考另经整数模型核对，合法替代表达和针对性错误都有实际证据。候选对自己综合网表的等价不是本任务的功能判据；必须核对比较点、黑盒与未证明状态。

完整必要验收通过为 1；确定的功能错误或有效候选的编译错误为 0；空／非法交付、工具故障、超时或不完整验收为 null，并分别归因。 终局奖励与独立保留评估分别记录；保留结果不回流求解。有限错误库或有限仿真不构成任意缺陷完备性证明，参考等价也只对明确比较语义成立。

## 从一份新工作区开始

以下是研究者的人工复现命令，需要[对应工具与本地配置](../toolchain.md)，输出目录应尚不存在。`test` 不会替你修改文件；先编辑指定交付物再测试。

```bash
python3 -m environment.artifact_task reset accumulator_wrap_repair_v1 .local/wrap-work
# 编辑 .local/wrap-work/accumulator.sv
python3 -m environment.artifact_task test accumulator_wrap_repair_v1 .local/wrap-work .local/wrap-public
python3 -m environment.artifact_task submit accumulator_wrap_repair_v1 .local/wrap-work .local/wrap-submit
```

需要带依赖清单的材料包时，使用 `python3 -m verification_resources.production produce reference-repair wrap .local/wrap-package`，再按[共同说明](README.md)核对和初始化。人工 CLI 的完整研究输出不应直接作为 Agent 工具反馈；真实试次由受控运行器投影反馈并执行预算。

## 已有什么证据，仍不能说明什么

[当前准入检查](../../experiments/verification-resources-v1/independent-reference-quality.json)覆盖该族的合法与错误对照；[评分实现](../../verifier/independent_formal/campaign.py)可核查判定机制。[研究报告](../verification-resources-tasks.md)分别列出各次真实模型试验、实际修复、失败与版本变化；[逐试次结果](../../experiments/verification-resources-v1/study-results-current.json)保留真实分母。

本页是冻结包外的使用指南，不改变原任务或准入身份。小样本与不同版本的结果不能合并为稳定成功率，也尚未证明模型参数训练收益。
