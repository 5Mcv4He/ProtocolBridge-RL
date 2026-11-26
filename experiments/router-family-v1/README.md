# 路由任务族 v1：可核查的生产证据

这份交付记录三种地址契约怎样从候选包进入真实验收，以及一条模型轨迹怎样使用其中一份包。先阅读[研究报告](../../docs/router-family-evaluation.md)理解结果与限制；需要复用时进入[生成方法和命令](../../task_families/router_v1/README.md)。本目录是经过筛选的证据，不是完整运行目录。

最关键的失败也保留在这里：旧生成验证器曾让丢失局部地址 bit 12 的错误 RTL 获得 Reward=1。修正后的门禁对**相同源码**给出 Reward=0。这是验证覆盖缺陷与修正证据，不计入 Agent 成功率，也不作为正确训练奖励使用。

## 按问题核查证据

| 要核查什么 | 入口 |
| --- | --- |
| 三种契约、包身份与准入 | [catalog.json](catalog.json)，链接各包 Spec、元数据、清单及 summary |
| 实际工业检查及源码绑定 | 各包的 `quality/result.json`、`quality/freeze.json` 与 `summary.json` |
| 旧方法为什么漏检、同一错误是否被检出 | [gap-analysis.json](calibration/gap-analysis.json)、[错误源码](calibration/faulty-offset-mask.sv)、[detection.json](calibration/detection.json) |
| 环境机制曾怎样拒绝候选 | [prototype-rejection.json](calibration/prototype-rejection.json) |
| 参考与判据共同出错时如何分类 | [oracle-fault.json](calibration/oracle-fault.json) |
| 模型试次是否预先限定 | [production-study-plan.json](production-study-plan.json)、[launch-plan.json](launch-plan.json) |
| 模型实际做了什么、看到什么 | [pilot-summary.json](pilot-summary.json)、[逐动作轨迹](pilot/r01-test_diagnostic/trace.json)、[审计](pilot/audit.json) |
| 私有输入本身能否被合法参考通过 | [input-qualification/result.json](input-qualification/result.json) |
| 生成复现与历史接口保留 | [reproduction.json](reproduction.json)、[production-interface-checks.json](production-interface-checks.json) |
| 成本及公开文件完整性 | [costs.json](costs.json)、[publication.json](publication.json) |

`launch-plan.json` 的 `model_started=false` 是运行前的冻结事实，保留不回改；真实启动与完成由后续试次证据记录。生成清单同样保留 `candidate_not_admitted`，是否准入由对应的外部门禁结果判断，不通过回填包内状态授予权限。

## 版本、身份与重建

生成器冻结于 `175dc9cbcc0c5762a099ee9346199af7480bec4b`，基础执行平台为 `194ffbe181601e4876035a35bfa49e7242317d41`。三份包都有独立 Task ID 和完整文件清单；其内部 `task002` 模块名仅表示复用后端。包内临时 Git commit 可能随生成时间变化，字节级重建核对的是 manifest SHA-256，不是临时提交时间。

无需商业工具即可重建候选并核对清单；这一步包含包内单元检查，但**不执行 RTL 仿真，也不重新授予准入**：

```bash
python3 task_families/router_v1/generate.py x2p_router_irregular_v1 .local/router-rebuild
python3 - <<'PY'
from pathlib import Path
assert Path('.local/router-rebuild/family-manifest.json').read_bytes() == Path('experiments/router-family-v1/irregular/family-manifest.json').read_bytes()
print('Generated source manifest matches')
PY
```

真正重跑工业门禁与模型试次，需要另行配置合法工具环境、求解隔离和 API。按照[生成器使用说明](../../task_families/router_v1/README.md)运行；私有向量不公开分发，公开哈希只能核对已有原件的一致性，不能凭哈希恢复这些输入。新的私有采样或模型采样产生新的实验身份，不声称逐字重现原始 Agent 输出。

## 公开范围与统计边界

发布任务规格、初始 RTL、明确错误对照、候选/提交、实际受控反馈、结果摘要、工具版本和来源哈希。完整商业日志、原始模型事件、精确发送上下文、私有向量和运行配置仍在可信存储。各子目录的导出清单记录原始证据哈希；它们用于追溯，不代表公开目录足以独立审计未分发的原件。

只有一条真实模型试次，三份任务是同一能力族的参数化契约。试次采用 Policy 白名单导出，尚未进入历史 v1–v3 Rollout Exchange；没有参数训练，也没有对诊断反馈效果或任务族整体难度作统计判断。
