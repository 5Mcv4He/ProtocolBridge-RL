# 任务生产第二阶段：证据入口

本目录保存经筛选的工程证据，不包含商业源码、私有原始输入或完整运行日志。先读[研究报告](../../docs/task-production-stage-v2.md)，再核对下列记录。原 X2P、UART 和历史模型记录不回写。

| 要核查的结论 | 证据 |
| --- | --- |
| UART 最后停止位边界曾误放行，修订 5 同源码拒绝 | [发现与复验](uart-stop-boundary-finding.json)、[32 项门禁](uart-quality-v5.json) |
| Checker 初版遗漏回绕后身份交互 | [被拒绝门禁](checker-quality-rejected-v1.json)、[同源码前后对照](checker-interaction-finding.json) |
| 深度 2、3 检查器任务可独立判定 | [36 项门禁](checker-quality-v2.json)、[28 项真实运行机制检查](checker-runtime-acceptance.json) |
| 两种状态寄存器优先级可独立判定 | [39 项等价与仿真检查](status-quality-v1.json) |
| 旧依赖清单可以遗漏条目；新版本要求完整集合 | [原反例与 v5 检查](materialization-dependencies.json)、[当前十包与 520 次遗漏拒绝](materialization-v6.json) |
| RFFE 有实际厂商读回活动，但尚无任务准入 | [活动复验](rffe-activity-recheck.json) |
| 四条模型轨迹没有挑选或替换 | [Checker 冻结计划](checker-study-plan.json)、[结果](checker-study-results.json)；[状态任务计划](status-study-plan.json)、[结果](status-study-results.json) |
| 实际动作、反馈与提交内容可重放核对 | [Checker 交换清单](checker-exchange/manifest.json)、[状态交换清单](status-exchange/manifest.json)、[反馈／提交篡改拒绝](status-audit-negative.json) |
| 成本与库存按用途分开 | [门禁成本](quality-costs.json)、[研究库存](exchange-inventory.json) |

旧 Checker 门禁源码保存在 `f0fa492`；修订 2 与首份交换导出器保存在 `68e6d97`。每份 gate、study plan 与 exchange manifest 另外绑定实际文件哈希；任务元数据中的 candidate 是生成时状态，不通过回填字符串获得准入。

训练侧记录只包含终局奖励与实际求解交互；evaluation 目录是独立保留评估，analysis 是离线说明。旧 UART 1–4 奖励保持历史值，已知边界缺口使它们不能自动继承当前训练候选用途。无 Token IDs、行为概率或精确权重版本；没有参数训练或训练收益证明。

本阶段已完成两个待核查问题、两类新工程契约及四条真实校准。非 UART 的新协议任务尚未完成；RFFE 的下一步是自建有限对象、独立语义检查与针对性错误对照。总体 30–50 库存和 30–60 试次只是长期建议规模，本次未为追求数量扩采。
