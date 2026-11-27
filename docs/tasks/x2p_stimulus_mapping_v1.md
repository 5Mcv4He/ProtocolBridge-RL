# 测试生成：暴露地址、字节写与读回缺陷

交付能够区分正确桥与错误桥的事务表。Agent 不写 RTL 或断言，而是选择输入，使固定可信 Scoreboard 能够观察到真实的功能差异。

[返回任务目录](../task-catalog.md) · [共同运行与权限](README.md) · [完整 Spec](../../tasks/x2p_stimulus_mapping_v1/spec.md)

## 要实现或触发的工程行为

只允许 1–32 笔顺序、4 字节对齐的 32 位读写。每笔为九个整数：[write,address,data,strobe,aw_delay,w_delay,wait,stall,error]。必须实际完成读与写；完整字段范围以 Spec 为准。

只做全字写，可能完全不触发 WSTRB 字节选择错误。局部字节写后再读回，才能观察未选中字节是否被错误覆盖。这个例子解释验证义务，不保证某一短事务表能检出全部必要错误。

## 提交什么，怎样判定

只修改 `stimulus.json`。初始材料见[工作文件](../../tasks/x2p_stimulus_mapping_v1/workspace/stimulus.json)，不可修改 Spec、参考、检查器或评分输入。只接受有界结构化 JSON，不接受可执行 SystemVerilog 测试台或脚本。

同一事务表先在合法设计通过，再对固定错误设计取得明确的功能／时序拒绝。公开调试、终局与保留使用不同错误集合。超时、编译失败或无条件报错不能算检出；错误数量本身不是奖励。

有效事务表活动不足或未检出必要错误为 0；合法设计通过且全部必要错误明确被检出为 1；空／非法表、合法设计无法完成或工具与验证问题为 null，并分别归因。 终局奖励与独立保留评估分别记录；保留结果不回流求解。有限错误库或有限仿真不构成任意缺陷完备性证明，参考等价也只对明确比较语义成立。

## 从一份新工作区开始

以下是研究者的人工复现命令，需要[对应工具与本地配置](../toolchain.md)，输出目录应尚不存在。`test` 不会替你修改文件；先编辑指定交付物再测试。

```bash
python3 -m environment.artifact_task reset x2p_stimulus_mapping_v1 .local/mapping-work
# 编辑 .local/mapping-work/stimulus.json
python3 -m environment.artifact_task test x2p_stimulus_mapping_v1 .local/mapping-work .local/mapping-public
python3 -m environment.artifact_task submit x2p_stimulus_mapping_v1 .local/mapping-work .local/mapping-submit
```

需要带依赖清单的材料包时，使用 `python3 -m verification_resources.production produce stimulus-design mapping .local/mapping-package`，再按[共同说明](README.md)核对和初始化。人工 CLI 的完整研究输出不应直接作为 Agent 工具反馈；真实试次由受控运行器投影反馈并执行预算。

## 已有什么证据，仍不能说明什么

[当前准入检查](../../experiments/verification-resources-v1/stimulus-quality.json)覆盖该族的合法与错误对照；[评分实现](../../verifier/stimulus/campaign.py)可核查判定机制。[研究报告](../verification-resources-tasks.md)分别列出各次真实模型试验、实际修复、失败与版本变化；[逐试次结果](../../experiments/verification-resources-v1/study-results-current.json)保留真实分母。

本页是冻结包外的使用指南，不改变原任务或准入身份。小样本与不同版本的结果不能合并为稳定成功率，也尚未证明模型参数训练收益。
