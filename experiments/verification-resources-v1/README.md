# 三类有限工程任务的证据入口

本阶段从成熟 X2P 方法扩展到 UART RTL、结构化测试生成和独立参考修复。阅读[研究报告](../../docs/verification-resources-tasks.md)理解为什么采用不同判据；本页用于核查版本、真实执行及复现。

## 先区分当前准入与历史结果

| 工程交付 | 当前验收 | 覆盖的契约变化 |
| --- | --- | --- |
| UART 发送 RTL | [修订 4，26 项](uart-quality-v4.json) | 无校验／偶校验；固定接口、256 帧、实际 busy 与相邻帧活动 |
| X2P 测试事务表 | [10 项](stimulus-quality.json) | 映射缺陷／时序缺陷；合法设计先通过，再检出指定功能错误 |
| 累加器修复 | [15 项](independent-reference-quality.json)与[整数锚点](independent-reference-anchors.json) | 回绕／饱和、状态更新优先级、独立参考等价完整性 |

UART 修订 1 未驱动 busy 请求，[相同错误源码漏检](uart-blindspot.json)促成修订 2；修订 2 未约束端口名称，[接口漏检](uart-interface-blindspot.json)促成修订 3；随后实际试次暴露[候选编译错误被误分类](uart-classification-finding.json)，修订 4 增加对应控制。旧准入、源码和模型奖励保留用于研究，不代表当前规则下的验证。事后[旧最终候选复验](uart-offline-final-recheck.json)仅属于离线分析，没有改写旧终局奖励。

## 预声明批次与实际交互

| 冻结计划 | 数量 | 对应交换 |
| --- | ---: | --- |
| [独立参考 v1](formal-study-plan.json) | 2 | [formal-exchange-v1](formal-exchange-v1/manifest.json) |
| [拒绝反馈 v2](formal-study-plan-v2.json) | 2 | [formal-exchange-v2](formal-exchange-v2/manifest.json) |
| [UART v1 与测试生成](uart-stimulus-study-plan.json) | 4 | [uart-stimulus-exchange](uart-stimulus-exchange/manifest.json) |
| [UART 修订 2](uart-verifier2-study-plan.json) | 2 | [uart-verifier2-exchange](uart-verifier2-exchange/manifest.json) |
| [UART 修订 3](uart-verifier3-study-plan.json) | 2 | [uart-verifier3-exchange](uart-verifier3-exchange/manifest.json) |
| [UART 修订 4](uart-verifier4-study-plan.json) | 2 | [uart-verifier4-exchange](uart-verifier4-exchange/manifest.json) |

[当前逐试次分析](study-results-current.json)与[库存](exchange-inventory.json)包含全部已启动记录。不同契约、反馈和验证器版本不合并成统一成功率；`training/` 是工具轨迹格式分区，不代表已经证明训练有效。`evaluation/` 独立保存，不用它筛选更好候选。原始回复、完整仿真／证明日志与私有运行记录保存在可信存储；公开制品包含可核查的动作、实际送达反馈、源码演变、提交、奖励和来源哈希。

[隔离检查](artifact-isolation.json)、[真实预算与提交检查](artifact-mechanism.json)、[阶段检查](artifact-phase-acceptance.json)和[审计篡改负例](audit-negative-checks-v2.json)分别检验权限、执行和记录一致性。阶段检查里的辅助 runner 哈希早于多交付物提示适配，它只证明所执行的 Session／grader 检查；真实模型执行身份以各批冻结计划为准，不以该辅助哈希代替。

## 复现需要哪些条件

需要依法配置 VCS、相应 VIP、Formality 与已有隔离 DSH Runtime。工具／Harness 版本与证据深度见[能力映射](capability-map.json)。本地后端配置被 Git 忽略，不能从公开摘要还原完整机器部署或私有运行记录。

[源码对应表](source-provenance.json)逐文件核对了六批计划对应的 Git 对象。先获取这些提交，再执行：

```bash
python3 scripts/check_artifact_provenance.py experiments/verification-resources-v1/source-provenance.json
python3 -m unittest tests.test_uart_interface tests.test_artifact_production \
  tests.test_artifact_extensions tests.test_artifact_feedback tests.test_artifact_session \
  tests.test_independent_formal tests.test_resource_batch_audit
```

以上只检查源码与控制逻辑，不会执行新 RTL 仿真。下面才会使用商业工具重新运行实际质量验收，每次指定不存在的新输出目录：

```bash
python3 -m verifier.independent_formal.quality .local/new-formal-quality
python3 -m verifier.stimulus.quality .local/new-stimulus-quality
python3 -m verifier.uart_tx.quality_v4 .local/new-uart-quality
```

真实 UART 模型复现使用 `environment.artifact_task.runner_v5`，以 `uart-verifier4-study-plan.json`、该计划中的 trial ID 和新的输出目录为参数。它会产生新的 API 调用，并核对所有冻结文件；模型采样未固定，不能保证重现相同源码或奖励。其他历史批次分别使用对应提交中的 runner／runner_v2／runner_v3。新研究应另建计划和身份，不把重复运行覆盖为旧样本。

[六份材料包验收](materialization-v4.json)检查有限生产、依赖与 reset；[生产器](../../verification_resources/production.py)不生成任意协议，也不包含商业源码或可跨机器复用的编译产物。

修订 3 的 8E1 试次因可信分类器缺陷中断，停止确认和终局评估均不可宣称完成。v6 审计保留这一不完整记录，并检查未在不确定停止状态下运行终局或保留评分；不能把它归为有效训练奖励样本。
