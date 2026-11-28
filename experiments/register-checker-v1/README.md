# 寄存器检查器任务：生产、验收与校准

[研究报告](../../docs/register-checker-evaluation.md)解释从设备实现到检查器交付的变化。本目录保留两种有限契约的真实证据，不包含私有事件向量、商业工具源码或部署记录。

| 环节 | 证据 |
| --- | --- |
| 工业准入 | [38 项门禁](quality.json)：12 合法、22 功能错误及 4 分类检查 |
| 材料与来源 | [三种材料篡改](materialization-checks.json)、[三种门禁篡改](admission-negative-checks.json) |
| 实际运行接口 | [Session 验收](session-acceptance.json)：真实后端、版本绑定、预算、冻结及停止后评分 |
| 真实模型 | [预声明计划](study-plan.json)、[两条实际结果](study-results.json) |
| 数据交付 | [v9 交换](exchange/manifest.json)、[实际事件重放](replay-audit.json)、[最新库存](exchange-inventory.json) |
| 成本 | [门禁、生产与求解分区](costs.json) |

## 从新候选到运行

需要已授权的 VCS 后端与本机私有连接配置；原生 Rollout 还需通过既有 native v3 安装与隔离验收。Python 控制工具使用 3.10 或更新版本。生成成功不等于准入。

```bash
# 生产完整候选包；新的模式不在生成域内时直接拒绝
python3 -m task_families.register_checker_v1.generate rw /path/to/new-candidate

# 在固定规范包与依赖下重新执行独立工业门禁
python3 -m verifier.register_checker.quality /path/to/new-gate

# 已准入包的严格材料化；不复制全部共享工程代码
python3 -m verification_resources.production_v6 materialize rw /path/to/new-package
python3 -m verification_resources.production_v6 check /path/to/new-package

# 新版公共入口同时支持此前任务；旧入口保持原版本
python3 -m environment.artifact_task.cli_v2 reset register_checker_rw_v1 /path/to/work
python3 -m environment.artifact_task.cli_v2 test register_checker_rw_v1 /path/to/work /path/to/new-public
python3 -m environment.artifact_task.cli_v2 submit register_checker_rw_v1 /path/to/work /path/to/new-submit

# 全新冻结计划与试次目录；切勿覆盖本目录的历史结果
python3 -m environment.native_tools.run_v4 /path/to/new-plan.json TRIAL_ID /path/to/new-trial
python3 -m scripts.check_native_replay_v2 /path/to/raw-trial --out /path/to/new-audit.json
python3 -m scripts.native_exchange /path/to/plan.json /path/to/raw-runs /path/to/new-exchange
```

手动 CLI 的 test/submit 用于可信操作者复现，会返回完整结果；模型仅通过受控 Session 获得公开字段，并在 submit 后停止，不能继续读取私有评分。新输入、源码或规则需要新的验收证据，不能修改历史哈希使旧门禁“通过”。

```bash
python3 -m unittest discover -s tests -p test_register_checker.py -v
python3 -m environment.register_checker_acceptance /path/to/new-session-acceptance
```

七项本地检查不能替代工业门禁。Session 验收使用可信参考作为夹具、没有模型调用；真实求解则以两条原生工具轨迹为准。独立保留评估不用于选择中间候选，没有事后补测。
