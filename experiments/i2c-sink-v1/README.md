# I²C 有限任务的验收与求解证据

本目录保存两份写入契约的准入、两条预声明模型试次和经过审查的数据交付。工程问题、失败原因与结论边界见[研究报告](../../docs/i2c-sink-evaluation.md)；操作入口见[任务指南](../../docs/tasks/i2c-write-sink.md)。

## 从被拒绝的生成包到通过准入

| 证据 | 实际范围 |
| --- | --- |
| [首轮拒绝](quality-rejected-v1.json) | 32 项中 6 个合法 word 对照不能编译，整体拒绝；8 个功能负例也只到编译失败，不能据此认定功能检出 |
| [修订 2 门禁](quality.json) | 32/32：12 次合法通过、16 个功能／时序拒绝、3 项无效交付、1 项语法错误 |
| [运行接口](runtime.json) | 28 项检查、6 次真实 VCS 调用；提交边界、预算与候选身份 |
| [完整材料依赖](materialization.json) | 12 份材料包与 reset、736 次依赖遗漏拒绝；不代表重新执行旧任务仿真 |
| [补充验收](acceptance-summary.json) | 171 项单元测试；历史 r3 哈希核对，明确未启动新 RTL 仿真 |
| [能力层次](capability-map.json)、[实际版本](toolchain.json)、[门禁成本](costs.json) | 来自真实日志的版本及对应运行耗时；不包含商业工具内容 |

拒绝版本源码位于提交 `1b0b227`，通过准入后的代码提交为 `c20f937`。Spec 保持相同；生成器与门禁修订单独记录。原始日志、编译物、实际输入和本机配置留在可信私有目录。

## 两条独立模型试次

[计划](study-plan.json)在第一次调用前冻结：deepseek-flash、DSH 0.2.2rc2、20 次动作、4 次公开测试、每契约一次。共启动并完成两条，不补抽、不替换；[汇总](study-results.json)分开记录终局与保留评分。

- byte：4 次公开 FAIL，5 次编辑；最终未公开测试版本终局／保留均为 1。
- word：4 次公开 FAIL，4 次编辑；提交相同已失败源码，终局／保留均为 0。

[行为证据](behavior-cases.json)区分模型实际收到的类别与可信侧的离线诊断，没有补写反馈，也没有事后仿真中间候选。它说明编译修复、ACK 修复和输出连接回归，不支持从两条轨迹推断稳定成功率或反馈因果效果。

## 数据如何核查与复用

[交换清单](exchange/manifest.json)逐文件绑定 [training](exchange/training/rollouts.jsonl)、[evaluation](exchange/evaluation/heldout.jsonl)、[analysis](exchange/analysis/offline.jsonl) 与候选内容。训练侧终局奖励不与保留分数相加；保留结果不用于选择更好的提交或训练候选。

[审计篡改反例](audit-negative.json)和[重复身份反例](audit-identity.json)均实际拒绝。运行目录不同不意味着它们是不同试次；同一计划和试次 ID 的副本不能重复计数。[新库存](exchange-inventory.json)在此前 125／85 的基础上增加两条，保持旧用途限制和历史奖励不变。

```bash
python3 -m scripts.analyze_artifact_study_v2 NEW_RESULTS.json RAW_BYTE RAW_WORD
python3 -m scripts.artifact_exchange_v3 NEW_EXCHANGE RAW_BYTE RAW_WORD
python3 -m scripts.check_artifact_audit_v3 RAW_SUBMITTED NEW_AUDIT.json
```

这些命令读取可信原始目录，不启动模型或 EDA。导出依赖原始响应与实际反馈的重放核对；只有公开汇总文件不足以重造原始轨迹。Token IDs、行为概率和精确模型权重版本未取得，不作无损 on-policy 数据或已证明训练收益的声明。
