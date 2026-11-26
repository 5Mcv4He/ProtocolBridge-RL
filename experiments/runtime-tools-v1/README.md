# Runtime tools v1：审查后的研究证据

本目录不是运行目录镜像。新模型试次只有两条：固定 Task003、同一真实错误起点、同一私有奖励/保留输入，判定与时间线条件各一条，均有效提交、Reward=0、保留评估=0，动作格式错误为零。结论及限制见[研究报告](../../docs/runtime-tools-evaluation.md)，工具使用见[接口文档](../../docs/runtime-experiments.md)。

| 文件 | 证明什么 |
| --- | --- |
| study-plan.json | 模型运行前的匹配条件、预算及最多两条试次计划 |
| task003-admission.json / admission-freeze.json | 冻结运行代码下的 Task003 正反对照、机制与隔离准入 |
| acceptance.json | 41 项实际运行时工具机制检查 |
| boundary-probes.json | 无效 RTL 与环境故障独立分类且未启动 EDA |
| matched-interface-check.json | 两组权限/预算相同，Prompt 只切换反馈模式 |
| observed-capacity-counterexample.json | 错误控制的实际事件表；不是模型轨迹 |
| study-report.json | 审计后自动汇总的两条试次、实际工具曝光、统计及成本 |
| behavior-evidence.json | 最终源文件/结果哈希、同一错误窗口及示例实验的对照事实 |
| final-runtime-*.sv | 两组模型的最终错误 RTL，研究者未修补 |
| input-qualification.json / qualification-freeze.json | 同一对冻结私有输入的正确参考复验，均通过；在求解停止后执行 |
| exchange/manifest.json | v3 交付完整性：本轮两条及此前独立综合试次一条，共三条，不能混合统计 |
| artifact-hashes.json | 本目录发布文件的 SHA-256（不包含清单自身） |

交换目录内：`training/rollouts.jsonl` 保存终局奖励和实际受控工具轨迹；`evaluation/heldout.jsonl` 仅用于保留评估；`analysis/offline.jsonl` 保存事后测量和包含保留执行的整体成本；`artifacts/` 是去重后的提示、Spec、读取及编辑内容。SDK 原始推理、私有向量、完整验证日志、商业文件和个人部署信息不公开。原始完整记录继续保存在可信本地。

运行代码冻结于 `22e24102fdd2924b9b16b29fe34bacdb1698526f`。后续发布修改只涉及数据交换分区、分析、测试和说明，没有修改冻结实验的 Prompt、工具运行、任务或评分规则。导出器、分析器、工具链、任务和输入哈希分别记录在对应清单内。

## 复核与重新运行

无商业工具即可核对公开文件完整性、运行单元测试及历史基线一致性：

```bash
python3 -m unittest discover -s tests -q
python3 -m environment.check_baseline
python3 - <<'PY'
import hashlib,json
from pathlib import Path
root=Path('experiments/runtime-tools-v1')
for name,digest in json.loads((root/'artifact-hashes.json').read_text())['files'].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
print('Published evidence hashes match')
PY
```

`check_baseline` 不运行 RTL。工业准入、运行时验收和新试次须有合法工具及独立可信后端，按[接口文档](../../docs/runtime-experiments.md)执行；新输出目录不得覆盖既有证据。私有原始向量不公开，公开哈希只支持同一性核查；公开使用者可以另冻输入重跑方法，不能宣称精确重现本轮私有输入。模型供应商默认采样也不保证重现相同 RTL。

拥有原始可信记录时，可重新审计并生成研究汇总：

```bash
python3 scripts/runtime_report.py RAW_VERDICT_COHORT RAW_OBSERVE_COHORT --out NEW_REPORT.json
python3 scripts/export_rollout_exchange.py --schema-version 3 --out NEW_EXCHANGE RAW_COHORT
```
