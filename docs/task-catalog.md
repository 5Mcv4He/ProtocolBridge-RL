# 多任务入口与准入

当前研究集合有 **11 个 X2P 任务身份与 6 个有限工程契约**。数量表示契约身份，不等于 17 种独立能力，也不表示它们具有相同的模型样本量或难度。

| 要复用什么 | 身份与材料来源 | 查询和运行路径 |
| --- | --- | --- |
| 原始单笔、路由、队列、解耦桥（4 个） | 根 [Registry](../tasks/registry.json) | `python3 scripts/tasks.py list`，下文给出生命周期命令 |
| 路由族、队列族、组合桥（7 个） | 各生成包及来源清单 | `python3 scripts/tasks.py --package PACKAGE list`，包内独立准入 |
| UART、测试生成、参考修复（6 个） | [有限交付 Registry](../tasks/artifact-registry.json) | `python3 -m environment.artifact_task list`；[逐任务说明与命令](tasks/README.md) |

这些入口复用控制与审计方法，但没有合并成同一个 CLI。根 `scripts/tasks.py list` 只列四个原始任务，不能用它的输出作为项目任务总数。完整研究记录与已审查轨迹的分母见[当前交换库存](../experiments/verification-resources-v1/exchange-inventory.json)，它不是任务准入证书。

## 四个原始 X2P 任务

原始四个 Task 定义共用[任务目录](../tasks/registry.json)与[元数据Schema](../tasks/registry.schema.json)。目录描述工程能力、协议、版本、Spec/初始RTL、验证后端、reset/test/submit接口、Policy和Reward契约；它不通过“status=ready”授予评测权限，也不把换随机种子计为新任务。

| Task | 新增能力要求 | 验收规则 |
|---|---|---|
| 001 revision3 | 单笔AXI4-Lite/APB转换、独立写半部、等待/错误/复位 | 原有基线与`validate_v3`保持不变 |
| 002 revision1 | 三目标译码、路由、返回选择、未映射DECERR | 两种参考+13错误对照+真实机制检查 |
| 003 revision1 | 两深度AW/W/AR容量、读写交叠、FIFO配对和仲裁 | 两种参考+15错误对照+真实机制检查 |
| 004 revision1 | APB执行与B/R消费解耦、完成快照、三深度非二次幂FIFO | 两种参考+14错误对照+真实机制检查；实际状态见[报告](task004-evaluation-report.md) |

```bash
python3 scripts/tasks.py list
python3 scripts/tasks.py show axil_to_apb4_queue_003
python3 scripts/tasks.py reset axil_to_apb4_queue_003 .local/queue-work
python3 scripts/tasks.py test axil_to_apb4_queue_003 .local/queue-work .local/queue-public
python3 scripts/tasks.py submit axil_to_apb4_queue_003 .local/queue-work .local/queue-submit
python3 scripts/tasks.py quality axil_to_apb4_queue_003 .local/queue-gate
python3 scripts/tasks.py rollout axil_to_apb4_queue_003 -- \
  --admission .local/queue-gate --out .local/queue-pilot \
  --protocol text-json-atomic-v2 --repeats 3 --limit 9 \
  --max-tokens 600000 --max-seconds 5400
```

统一入口调用既有任务专用实现，不重写UVM或奖励规则；直接使用`python3 -m environment.policy_experiment --task ...`仍有效。手动test/submit会先检查工作区Spec与所选任务一致，防止给相同端口的RTL套错功能契约。元数据非法、任务不存在、路径越界或版本不一致会拒绝执行。

002/003/004的Rollout仍要求当前源码及工具链匹配的实际Quality Gate。当前门禁保守冻结整个environment/verifier/fixtures/tests，因此增加其他任务代码也会使旧准入不能在新checkout直接复用；历史结果仍属于原提交。需要对新checkout重新验收，不能改旧freeze来“升级”。001默认命令、历史Spec及结果不变。

这个基础目录负责统一管理与调用；自动生产由独立的[有限路由任务族](task-family-production.md)与[队列任务族](queue-family-production.md)承担。增加一个Task需要独立契约、实现/错误对照、实际验证、明确版本与人类README。更新目录后仍须在控制器支持的任务集合中显式登记，避免任意元数据动态扩大求解权限。

验证目录和CLI：`python3 scripts/test_task_catalog.py`。这组测试不消耗VCS许可证；真正的RTL验收使用上面的quality命令。`quality`对001调用原有正反对照，对002/003/004执行新门禁；两者的历史验收范围不能混称。

## 生成任务怎样进入同一个执行路径

[路由任务族 v1](../task_families/router_v1/README.md)从 Task002 复用三目标、单事务的协议与验证基础，生成不同地址窗口契约。每份候选拥有自己的 Registry、Spec、验证后端和源码清单；正式 Rollout 仍需该包及工具链匹配的工业准入证据。原有四任务目录和历史结果不变。

[队列任务族 v1](../task_families/queue_v1/README.md)则从 Task003 生成 1/1/1、3/3/3 和 1/1/3 的 AW/W/AR 容量契约，增加与实际事件绑定的容量、回绕和退休边界义务。它使用同一包入口，但保留队列专用 Scoreboard；不是将路由判据套用于时序状态问题。[来源绑定目录](../experiments/queue-family-v1/catalog.json)记录三份准入及待校准状态。根目录 `list` 仍列四个基础任务，生成实例使用各自 `--package` 目录，不混入原冻结 Registry。

通过 `python3 scripts/tasks.py --package PACKAGE ...` 可使用同样的 list/reset/test/submit/quality/rollout 操作。相对工作路径以包为基准。参数化实例不等于独立工程能力，包清单核对也不等于质量验收；生成、准入和求解的区别见[生产方法](task-family-production.md)。

## 任务契约与研究元数据分开更新

[原始 X2P 工程阶段研究索引](../experiments/engineering-stage-research-index.json)（[上一阶段索引](../experiments/task-research-index.json)保留）将每个Task的能力、协议、验证后端、版本、污染风险与各次真实实验关联，提供逐Policy样本量、0/1/null、反馈曝光、Token、耗时和来源哈希。由`scripts/research_index.py`从已审查证据生成，不合并独立生成与修复，也不授予执行准入。每次有新结果更新研究索引，保持冻结Spec/任务包不变。

原始 X2P 的对应实测：[001批量研究](batch-evaluation-report.md)、[002路由](task002-evaluation-report.md)、[003独立生成](task003-evaluation-report.md)、[003同起点修复](task003-repair-report.md)、[003工程工具对照](engineering-tools-evaluation.md)、[004执行/响应解耦](task004-evaluation-report.md)。当前研究报告由此固定索引链接；历史冻结任务包不为追加结果回改。

## 组合契约与环境条件分别计数

[路由／退休组合契约](composed-task-production.md)增加一个 `x2p_routed_queue_v1` Task ID。两种合法结构、19 个错误对照、25 个完整 case、23 个公开 case、48 项需求覆盖和 40 项机制检查已通过[源码绑定的工业验收](../experiments/composed-stage-v1/composed-v2/summary.json)。它与四个原始任务、六个已验收生成实例构成 11 个任务身份，不等于 11 种独立工程能力。

[综合工程环境](engineering-lab.md)则复用 `x2p_queue_three_v1` 的同一 Spec。工具配置和候选版本反馈改变时，需要新的环境冻结与验收，不能增加任务数量，也不能继承旧环境的准入哈希。任务库库存、模型试次与训练候选应分别统计。

[组合阶段研究库存](../experiments/composed-stage-v1/task-inventory.json)逐项区分任务来源、契约差异、准入证据和模型试次状态；三条新试次及候选回退见[研究报告](composed-environment-evaluation.md)。初版组合验证曾漏掉目标相关复位错误，当前使用验证器修订 2，旧证据仍保留供核查。

## 三种新的有限工程交付

X2P 的 11 个任务身份保持不变。另有[有限交付 Registry](../tasks/artifact-registry.json)，列出 UART 8N1／8E1、mapping／timing 测试生成、回绕／饱和累加器修复，共六个契约。它们分别使用工业解码加周期模型、固定设计与 UVM Scoreboard、独立参考 Formality；不能沿用 X2P 的“提交 bridge.sv”假设。

[六份任务使用指南](tasks/README.md)连接每个契约的 Spec、可修改材料及运行命令；[任务与研究说明](verification-resources-tasks.md)解释能力边界、正反对照、真实漏检与实际模型结果。`python3 -m environment.artifact_task list` 查询有效入口；`python3 -m verification_resources.production` 提供有限生产、依赖检查和初始化。Registry 是当前证据入口，准入仍要求哈希严格匹配；任务创建时的元数据与历史结果不回填。
