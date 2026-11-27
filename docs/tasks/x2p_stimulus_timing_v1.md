# 测试生成：让等待、背压与通道错开发生

构造实际触发时序风险的激励。相比 mapping 实例，这里要求等待、响应背压、AW 先到和 W 先到都真实发生，不能仅在描述中声明覆盖。

[返回任务目录](../task-catalog.md) · [共同运行与权限](README.md) · [完整 Spec](../../tasks/x2p_stimulus_timing_v1/spec.md)

## 要实现或触发的工程行为

事务表仍为 1–32 笔顺序读写及九个整数字段。aw_delay/w_delay 从该写启动起算；wait 是 APB Access 等待周期；stall 是响应出现后的额外阻塞，驱动还有一个 ready 反应周期，0 不表示预先 ready。

让 AW 与 W 分别先到，可区分“同时到达才能执行”的错误桥；插入 APB 等待，可以检查桥是否在 PREADY 之前过早完成请求。具体激励与固定检查器共同决定检出能力，不能以延迟参数非零代替实际事件账目。

## 提交什么，怎样判定

只修改 `stimulus.json`。初始材料见[工作文件](../../tasks/x2p_stimulus_timing_v1/workspace/stimulus.json)，不可修改 Spec、参考、检查器或评分输入。只接受有界结构化 JSON，不接受可执行 SystemVerilog 测试台或脚本。

固定 UVM Scoreboard 检查事务，执行账目确认必要行为。合法设计通过且必要错误均有明确功能／时序拒绝才获得奖励。公开、终局与保留的错误集合分开，不能通过修改检查器或让全部 DUT 超时获得成功。

有效事务表活动不足或未检出必要错误为 0；合法设计通过且全部必要错误明确被检出为 1；空／非法表、合法设计无法完成或工具与验证问题为 null，并分别归因。 终局奖励与独立保留评估分别记录；保留结果不回流求解。有限错误库或有限仿真不构成任意缺陷完备性证明，参考等价也只对明确比较语义成立。

## 从一份新工作区开始

以下是研究者的人工复现命令，需要[对应工具与本地配置](../toolchain.md)，输出目录应尚不存在。`test` 不会替你修改文件；先编辑指定交付物再测试。

```bash
python3 -m environment.artifact_task reset x2p_stimulus_timing_v1 .local/timing-work
# 编辑 .local/timing-work/stimulus.json
python3 -m environment.artifact_task test x2p_stimulus_timing_v1 .local/timing-work .local/timing-public
python3 -m environment.artifact_task submit x2p_stimulus_timing_v1 .local/timing-work .local/timing-submit
```

需要带依赖清单的材料包时，使用 `python3 -m verification_resources.production_v3 produce stimulus-design timing .local/timing-package`，再按[共同说明](README.md)核对和初始化。人工 CLI 的完整研究输出不应直接作为 Agent 工具反馈；真实试次由受控运行器投影反馈并执行预算。

## 已有什么证据，仍不能说明什么

[当前准入检查](../../experiments/verification-resources-v1/stimulus-quality.json)覆盖该族的合法与错误对照；[评分实现](../../verifier/stimulus/campaign.py)可核查判定机制。[研究报告](../verification-resources-tasks.md)分别列出各次真实模型试验、实际修复、失败与版本变化；[逐试次结果](../../experiments/verification-resources-v1/study-results-current.json)保留真实分母。

本页是冻结包外的使用指南，不改变原任务或准入身份。小样本与不同版本的结果不能合并为稳定成功率，也尚未证明模型参数训练收益。
