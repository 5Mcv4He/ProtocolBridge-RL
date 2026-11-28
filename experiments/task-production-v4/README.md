# 原生动作交付与数据用途：证据入口

本阶段检验模型提出的工具动作能否准确执行、反馈是否真正送达，以及历史轨迹可以支持什么分析。共五条真实工程试次，分属 native v2（3 条）与 fixed-file native v3（2 条）；没有替换失败样本，没有事后重评中间候选。任务与独立 Verifier 保持原版。

先读[研究报告](../../docs/native-tool-delivery-evaluation.md)理解接口与工程结果的区别，再按下表核查证据。新协议没有替换历史文本 JSON 环境。

| 要核查什么 | 证据 |
| --- | --- |
| 调用前决定了什么 | [v2 计划](native-study-plan.json)、[v3 计划](fixed-file-study-plan.json) |
| 安装后的实际 SDK 权限和预算 | [原生机制检查](native-mechanism-acceptance.json)、[当前 v3 来源匹配验收](native-runtime-acceptance.json) |
| 每条试次的结果与成本 | [逐条结果](native-study-results.json) |
| 原始提案、执行、反馈与候选 | [v2 交换](native-v2-exchange/manifest.json)、[v3 交换](native-v3-exchange/manifest.json) |
| 控制器状态能否从真实事件复现 | [五条重放](native-offline-replay.json)、[六种篡改拒绝](native-replay-challenges.json) |
| 库存如何避免重复计数 | [137 条记录／97 条轨迹](exchange-inventory.json) |
| 历史数据能支持哪些用途 | [规则与解释](../../docs/trajectory-data-uses.md)、[132 条历史记录用途候选](historical-data-use-candidates.json) |

首批的机制检查保留当时源码哈希，不用后续版本覆盖；当前 installed-v3 验收单列。四条 API 运输夹具仅验证接口，不计入工程任务库存。零推理调用的 SDK 检查仍可能访问服务的模型目录，不等于零网络请求。

## 重用与复核

需要已授权商业后端、来源匹配的任务准入、DSH SDK／Runtime，以及独立安装的无特权 worker。安装入口和本机连接配置属于部署方职责；新入口不覆盖旧 worker，不创建常驻服务。不要把私有配置、密钥或原始仿真日志放进本目录。

```bash
# 本地权限、预算、审计与数据用途测试；无模型和 EDA 调用
python3 -m unittest discover -s tests/native_tools -v
python3 -m unittest discover -s tests -p test_trajectory_uses.py -v

# 已安装版本的实际 SDK 执行器验收；输出必须是新目录
python3 -m environment.native_tools.acceptance --out /path/to/new-acceptance

# 独立的新试次；计划中的所有源码和 Prompt 必须严格匹配
python3 -m environment.native_tools.run_v3 \
  /path/to/new-frozen-plan.json TRIAL_ID /path/to/new-trial

# 只重放真实记录，不重跑模型／EDA，不回填奖励
python3 -m scripts.check_native_replay /path/to/raw-trial --out /path/to/new-audit.json
python3 -m scripts.challenge_native_replay /path/to/submitted-raw-trial /path/to/new-negative-audit.json
python3 -m scripts.native_exchange /path/to/plan.json /path/to/raw-runs /path/to/new-exchange
```

控制器与离线工具使用 Python 3.10 或更新版本；实际隔离 worker 使用 Python 3.10。需要临时部署授权时可使用 `--ask-sudo-password`，凭据仅通过交互输入进入内存。实验 API Key 从环境读取，不属于计划或公开证据。

复现实验必须创建新计划身份和新输出路径；不能覆盖这五条历史结果。计划以基准 Git 提交加逐文件哈希冻结，公开清单不包含私有原始输入。模型权重版本、随机种子和精确 API 费用不可取得；新的调用不保证复现相同模型轨迹。

公开摘要和交换包足以核查主要结果、源码演变与真实观察；完整离线重放还需要可信侧原始 SDK 事件与评分结果。不存在这些原始材料时，不能用摘要补造它们。

## 后续阶段与数据用途

本目录最初五条接口校准保持冻结。[第四阶段综合报告](../../docs/task-production-stage-v4.md)连接后续寄存器检查器、SWD和结构优化的四条独立试次；它们各有单独计划、门禁与交换包。`native-use-review/`只在训练侧对新9条记录做独立用途审查，不改写旧132条筛选或混合成功率。
