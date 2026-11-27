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


## 实际结果与独立后续

首批四条全部按计划结束：Checker 深度 5 与位计数提交通过，RFFE W1C 与 I²C 组字提交未修改起点，均失败。没有替换失败样本。随后另行冻结一次 RFFE 动作拒绝提示改进试次；它完成三次有效编辑和三次失败检查，但耗尽 20 次动作未提交，Reward=null，不执行终局或保留评估。两批不能合并为方法成功率。

| 核查对象 | 入口 |
| --- | --- |
| 首批结果与工具轨迹 | [结果](study-results.json)、[v8 清单](exchange/manifest.json) |
| 后续预声明、结果与工具轨迹 | [计划](action-diagnostic-plan.json)、[结果](action-diagnostic-results.json)、[独立交换清单](diagnostic-exchange/manifest.json) |
| 候选变化与实际曝光 | [行为案例](behavior-cases.json)，没有中间候选事后评分 |
| 后续机制与审计反例 | [16 项机制验收](diagnostic-runtime-v3.json)、[篡改与重复拒绝](diagnostic-audit-validation.json) |
| 来源、累计库存与成本 | [源码对应关系](source-provenance.json)、[132／92 分母](exchange-inventory.json)、[五条实际成本](rollout-costs.json) |

后续使用 runner v11／Session v5，首批使用 runner v10／Session v4。后续只修改固定的动作拒绝说明；两者都不替模型拆分多动作回复或修正非法字段。

```bash
# 后续条件，单条试次；另用全新目录，仍产生实际 API 与 EDA 成本
python3 -m environment.artifact_task.batch_v3 \
  experiments/task-production-v3/action-diagnostic-plan.json .local/diagnostic-study-new

# 不调用 EDA 或 API：核对冻结源码能否在记录的 Git 提交中找到
python3 -m scripts.check_artifact_provenance \
  experiments/task-production-v3/source-provenance.json
```

两份计划要求各自冻结源码，不应把最新 checkout 的任意修改解释为原实验条件。复核与导出原始记录需要可信本地数据；公开包保留经审查的交互与内容哈希，没有私有向量、完整日志或商业依赖。无 Token IDs、行为概率、精确模型权重和货币账单时，不补造这些字段。

[交付检查](delivery-validation.json)记录单元测试、历史基线与源码核对，以及本地阅读预览；后两者不冒充新的 RTL 仿真，预览也不等同于 GitHub 实际渲染。
