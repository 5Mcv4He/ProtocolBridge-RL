# 001 X2P：批量固定模型研究证据

[研究报告](../../docs/batch-evaluation-report.md) · [冻结与执行契约](../../docs/batch-study.md)

本目录按交互协议与研究类型分别保存结果，不能将不同批次混合计算策略成功率。历史 `industrial-v3` 和 `policy-v1` 未改写。

| 目录 | 研究 | 状态与分母 |
|---|---|---|
| [text-v1-stopped](text-v1-stopped/batch-analysis.md) | 原文本协议，自主生成 | 17次全部保留；扩展阶段因动作格式质量不合格停止，未完成原计划30次 |
| [text-v2-independent](text-v2-independent/batch-analysis.md) | 新动作协议，自主生成 | 30次；A7/10、C8/10、E8/10；完整审计与质量门槛通过 |
| [text-v2-repair](text-v2-repair/batch-analysis.md) | 同一真实错误RTL，C/E配对修复 | 6次；C1/3、E3/3；全部真实FAIL曝光后修改，审计通过 |

每个目录中的 `batch-analysis.json`、`trial-measurements.csv` 保留所有启动试次；`experiment.json` 记录源码／Policy／Prompt／输入哈希、模型与工具链。`all-trial-provenance.json` 为每个启动试次关联会话、输入及原始轨迹／候选哈希；`publication.json` 列出选择公开的轨迹及导出文件哈希。`feedback-history.json` 单列全部试次实际收到的公开反馈及对应源码哈希。选择只减少重复日志体积，不改变样本分母。

典型轨迹包含实际投影反馈、动作是否执行、候选源码、最终提交、私有及保留集的精简结果、模型会话标识和原始证据哈希。源码读写正文在精简轨迹中用哈希关联，实际候选另存为 `.sv`。完整SDK回包、EDA日志、私有向量和本机部署细节留在可信本地，不在GitHub。

```bash
# 只复核公开汇总的算术与区间，不调用API或VCS
python3 scripts/recompute_statistics.py experiments/batch-study-001/text-v1-stopped
python3 scripts/recompute_statistics.py experiments/batch-study-001/text-v2-independent
python3 scripts/recompute_statistics.py experiments/batch-study-001/text-v2-repair
```

完整审计需要可信侧原始输入／输出，运行 `scripts/audit_policy.py`；RTL重放需要授权工具及对应冻结输入。公开哈希不能还原私有向量，也不能证明尚未测试的输入都正确。源代码语言门禁通过、有效提交、公开PASS、私有Reward=1分别统计。

本目录中的失败包含动作协议错误、未生成候选、未提交和真实RTL错误；null不自动计为功能失败。不是RL参数训练，也不是完整工业签核。
