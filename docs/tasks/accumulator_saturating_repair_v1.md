# 饱和累加器：正确识别无符号进位

修复 8 位累加器的溢出与状态控制。相比回绕实例，这里需要在数学和超过 255 时保持上界，测量的是无符号进位判断，而不是简单截断结果。

[返回任务目录](../task-catalog.md) · [共同运行与权限](README.md) · [完整 Spec](../../tasks/accumulator_saturating_repair_v1/spec.md)

## 要实现或触发的工程行为

低有效同步复位优先，其次 load 装载，再其次 enable 累加，否则保持。累加数学和大于 255 时输出 255，否则输出该和；所有控制组合合法。

例如 250+10 应饱和为 255，而 127+1 应得到 128，不能把最高位为 1 当作溢出。若同时 load=1，则装载 value，不执行饱和加法。比较检查任意 8 位当前状态，不允许增加流水线周期。

## 提交什么，怎样判定

只修改 `accumulator.sv`。初始材料见[工作文件](../../tasks/accumulator_saturating_repair_v1/workspace/accumulator.sv)，不可修改 Spec、参考、检查器或评分输入。RTL 必须自包含并保持契约接口；宏、include、外部模块、文件访问等限制见 Spec。

独立参考 Formality 与参考语义的整数模型锚点承担不同职责：前者核对候选等价，后者帮助审查参考是否符合契约。合法替代实现、进位和优先级等错误对照经过实际检查；不完整证明不能当作 PASS。

完整必要验收通过为 1；确定的功能错误或有效候选的编译错误为 0；空／非法交付、工具故障、超时或不完整验收为 null，并分别归因。 终局奖励与独立保留评估分别记录；保留结果不回流求解。有限错误库或有限仿真不构成任意缺陷完备性证明，参考等价也只对明确比较语义成立。

## 从一份新工作区开始

以下是研究者的人工复现命令，需要[对应工具与本地配置](../toolchain.md)，输出目录应尚不存在。`test` 不会替你修改文件；先编辑指定交付物再测试。

```bash
python3 -m environment.artifact_task reset accumulator_saturating_repair_v1 .local/saturating-work
# 编辑 .local/saturating-work/accumulator.sv
python3 -m environment.artifact_task test accumulator_saturating_repair_v1 .local/saturating-work .local/saturating-public
python3 -m environment.artifact_task submit accumulator_saturating_repair_v1 .local/saturating-work .local/saturating-submit
```

需要带依赖清单的材料包时，使用 `python3 -m verification_resources.production_v3 produce reference-repair saturating .local/saturating-package`，再按[共同说明](README.md)核对和初始化。人工 CLI 的完整研究输出不应直接作为 Agent 工具反馈；真实试次由受控运行器投影反馈并执行预算。

## 已有什么证据，仍不能说明什么

[当前准入检查](../../experiments/verification-resources-v1/independent-reference-quality.json)覆盖该族的合法与错误对照；[评分实现](../../verifier/independent_formal/campaign.py)可核查判定机制。[研究报告](../verification-resources-tasks.md)分别列出各次真实模型试验、实际修复、失败与版本变化；[逐试次结果](../../experiments/verification-resources-v1/study-results-current.json)保留真实分母。

本页是冻结包外的使用指南，不改变原任务或准入身份。小样本与不同版本的结果不能合并为稳定成功率，也尚未证明模型参数训练收益。
