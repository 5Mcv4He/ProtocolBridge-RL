# 多验证资源任务生产：证据入口

本阶段把 RFFE、综合结构约束、I²C 协议骨架补全及 Checker 新深度转成独立验收的任务。研究问题和工程例子见[阶段报告](../../docs/task-production-stage-v3.md)；本目录连接可核查的证据，不保存商业工具、私有向量或原始运行日志。

## 从任务门禁到实际求解

| 证据 | 可以说明什么 |
| --- | --- |
| [任务库存](task-inventory.json) | 31 个任务身份；I²C 两个骨架起点与原功能契约的关系，不能把身份数当作能力数 |
| [能力映射](capability-map.json) | 各资源处于工业准入还是实际模型校准层级；厂商例程不会自动升级为任务能力 |
| [Checker 39 项](checker-quality-v3.json) | 深度 1／5 的合法结构、身份／容量／回绕错误及无效提交 |
| [RFFE 33 项](rffe-quality-v2.json) | 两种更新规则的协议、实际引脚、地址和寄存器状态判断 |
| [RFFE 同源码复验](rffe-configuration-review.json) | 未限定读模式造成可信配置分歧；相同候选、输入在明确模式后复验 |
| [综合修复 31 项](bitfold-quality-v1.json) | 全输入功能、DC 结构、独立参考及自身网表两条等价路径 |
| [I²C 补全 18 项](i2c-completion-quality-v1.json) | 正确骨架的新起点仍接受原完整协议与功能检查 |
| [107 项运行机制](runtime-acceptance-v2.json) | 27 次实际后端调用，权限、预算、当前源码、停止后评分与阶段分离 |
| [隔离探针](runtime-isolation.json) | 现有受限 worker 的实际检查及未实现的试次间文件隔离边界 |
| [材料化验收](materialization.json) | 二十份包可初始化，八份新包的完整依赖／文件遗漏被拒绝 |
| [成本](quality-costs.json)、[工具链](toolchain.json) | 本次实际门禁调用的耗时及日志头版本，不是通用性能承诺 |

## 预声明的分层采样

[冻结计划](study-plan.json)在首次模型请求前确定四条独立试次，每类一条：深度 5 Checker、RFFE W1C、置位计数综合修复、I²C 组字补全。统一 deepseek-flash、reasoning off、20 次动作、4 次公开检查；精确权重、随机种子与采样温度无法固定的部分明确记录。

最初考虑八条，但实际构建存储成本使本批在采样前缩为均衡的四类各一条。减少的是样本数，没有降低工具预算或评分标准。样本选择基于契约义务，不依据任何本批模型结果。源码、输入、提示、预算、停止条件与离线分析范围都在计划中；模型原始回复与每个候选由可信本地保留。

```bash
# 需要匹配的源码、合法 EDA 环境、已配置隔离 worker 与模型服务。
# 使用全新输出目录；恢复时同一目录只保留、跳过已完成记录，不重新采样。
python3 -m environment.artifact_task.batch_v2 \
  experiments/task-production-v3/study-plan.json .local/resource-study-new
```

这条命令会产生真实 API 与 EDA 成本。若冻结源码、隔离或可信评分不满足条件，应停止并保留不可判定记录。单次结果不能证明稳定难度或训练收益，独立保留评估不作为训练奖励或选样标准。
