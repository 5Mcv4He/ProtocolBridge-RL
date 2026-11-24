# Policy v1：公开证据入口

[结果与限制](../../docs/policy-evaluation-report.md) · [策略机制](../../docs/observation-policy.md) · [仓库首页](../../README.md)

这是 revision 3 的 001 X2P 上新增的固定模型 Rollout 对照，执行代码冻结于 `1dc35011415f3ba110816ff56f18043112bf3744`。原 `industrial-v3/` 证据未覆盖。正式三次试次都使用 UTM 内真实 DSH／DeepSeek API 和 VCS／AMBA VIP／UVM，未由人工替模型编辑 RTL。

| 正式试次 | 动作／编辑／公开调用 | 私有 Reward | 保留评估 | 轨迹 |
|---|---|---|---|---|
| A | 7／2／0 | 1.0 | 1.0 | [spec_only](r01-spec_only/trace.json) |
| C | 7／2／1 | 0.0 | 0.0 | [test_verdict](r01-test_verdict/trace.json) |
| E | 6／0／0 | 0.0 | 0.0 | [test_diagnostic](r01-test_diagnostic/trace.json) |

E 的多动作回复被拒绝后提交了初始模板，没有获得诊断反馈。此处不表示 A 更好或 E 更差；每组仅一次。正式批次前另有因动作解析缺陷排除的开发试跑，保留在 [bringup.json](bringup.json)，未计入此表。

## 文件怎么读

| 文件 | 用途 |
|---|---|
| [experiment.json](experiment.json) | 预设组序、三个 Policy、prompt／源码哈希、配对输入哈希 |
| [summary.json](summary.json) | 原始运行器汇总：提交、奖励、动作、公开调用、首候选和保留结果 |
| [analysis.json](analysis.json) | 离线提取实际 Token、拒绝动作、反馈是否送达、会话跨度 |
| [audit.json](audit.json) | 完整本地证据审计：实际 SDK 输入、动作解码、源码链、权限预算、配对 suite；本次通过 |
| [mechanism/result.json](mechanism/result.json) | 模型运行前的 31 项真实 VCS 机制验收，七次 grader 调用 |
| [runtime-probe.json](runtime-probe.json) | 实际 SDK／Python／EDA 版本与 SDK 配置字段 |
| [validation.json](validation.json) | 发布单元检查、基线一致性、Python 语法兼容和审计结果 |
| [publication.json](publication.json) | 本公开证据目录文件的 SHA-256 |

每个 `r01-*` 目录包含 `policy.json`、`freeze.json`、`initial-prompt.txt`、实际生效的 `candidate-*.sv`、`submission/bridge.sv` 和 `metrics.json`。`public-*/result.json`、`submission/grade/result.json`、`reserved-evaluation/result.json` 是白名单精简后的真实判定与 UVM 计数，不是伪造演示日志。

`trace.json` 的公开测试反馈保持实际发送内容；读取内容和编辑大文本以哈希代替，编辑另有候选文件。被拒绝的编辑没有候选文件，不能当作执行成功。`observation-provenance.json` 对实际发送的逐轮 prompt 记录哈希；`harness-provenance.json` 记录真实会话、worker UID/PID 和请求参数。

`raw-evidence-sha256.json` 为可信侧原始文件建立索引。商业仿真日志、私有向量、完整 SDK 响应和机器部署配置不上传。原始证据在开发机 `.local/policy-pilot-02/` 与对应 UTM release 保留，开发试跑在 `.local/policy-pilot-01/`；这两个目录均不属于公开交付。临时编译缓存已在取回证据后清理，不能把旧 cache 路径当成可用缓存。

## 复现边界

完整命令见[实验报告](../../docs/policy-evaluation-report.md#复现与证据)。重新运行入口会生成新配对输入，保持同轮三组一致；公开哈希本身不能恢复这次私有原始向量。复用本次冻结向量需要可信侧输入副本及授权 EDA。已发布报告只证明列出的真实样本和机制检查，不声称统计显著、完整形式证明或 RL 训练已完成。
