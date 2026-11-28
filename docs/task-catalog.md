# 多任务入口与准入

历史研究集合有 **11 个 X2P 与 24 个有限工程任务身份**。其中两个 I²C 补全任务复用已有功能契约；35 个身份不等于 35 种独立能力，也不表示它们具有相同的模型样本量或难度。

| 要复用什么 | 身份与材料来源 | 查询和运行路径 |
| --- | --- | --- |
| 原始单笔、路由、队列、解耦桥（4 个） | 根 [Registry](../tasks/registry.json) | `python3 scripts/tasks.py list`，下文给出生命周期命令 |
| 路由族、队列族、组合桥（7 个） | 各生成包及来源清单 | `python3 scripts/tasks.py --package PACKAGE list`，包内独立准入 |
| UART／I²C／RFFE／SWD、测试生成、参考修复、Checker、综合修复与结构优化（24 个） | [追加 Registry（含原目录）](../tasks/artifact-registry-v4.json) | `python3 -m environment.artifact_task.cli_v4 list`；[逐任务说明与命令](tasks/README.md) |

这些入口复用控制与审计方法，但没有合并成同一个 CLI。根 `scripts/tasks.py list` 只列四个原始任务，不能用它的输出作为项目任务总数。完整研究记录与已审查轨迹的分母见[当前交换库存](../experiments/task-space-v1/exchange-inventory.json)，它不是任务准入证书。

## 新契约生成与当前可运行池

新生产研究另外生成两轮各 20 份地址契约。当前五份实例有修订后来源匹配准入：`batcha`、`batche`、`roundwordn`、`roundworda`、`roundwordq`（完整身份均为 `x2p_router_<名称>_v1`）。其余候选与历史通过版本分别记录，不自动计为当前可运行任务。[生产报告](task-space-production.md)给出工程差异、拒绝原因与实际成本；[工业证据](../experiments/task-space-v1/production/word-controls-v1/manifest.json)不能被材料生成结果代替。

```sh
python3 -m environment.package_pool_v2 PRIVATE_ADMISSIONS PRIVATE_CONFIG
```

该入口重新核对任务包及运行机制依赖，输出当前匹配的任务和准入身份；它不是把公开摘要读成永久许可证。[生产与运行说明](../task_families/router_v6/README.md)连接契约构造、静态生产、工业门禁、运行准入及原生批量求解。旧入口保持原有任务范围。

两份新增[路由与队列组合实例](../task_families/composed_v2/README.md)另已完成实例功能对照，但尚未具备对应运行准入，不进入上述五份任务池。[APB 寄存器族](../task_families/apb_register_v1/README.md)的两份契约后来完成了设备语义对照与独立运行准入；mixed 另有一条真实模型求解，status 尚未模型校准。[跨域入口](../environment/task_pool_v1.py)通过私有准入／配置索引核对五份路由加两份寄存器，共七份当前匹配的环境。角色或实例功能资格本身仍不能自动授予任务运行权限。这样可以分别查看生产能力、验证进度与真正可启动的求解任务。

```sh
python3 -m environment.task_pool_v1 PRIVATE_POOL_INDEX.json
```

新寄存器的验收、启动与审计命令见[运行说明](register-family-runtime.md#怎样复用运行入口)。两份仅有功能层资格的组合任务仍不计入当前池。

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

## 不同形式的有限工程交付

X2P 的 11 个任务身份保持不变。另有[有限交付 Registry](../tasks/artifact-registry.json)，列出 UART 8N1／8E1、mapping／timing 测试生成、回绕／饱和累加器修复，以及深度 2／3 Checker、两种优先级状态寄存器，以及 I²C 字节／组字交付，构成前十二个契约；此前阶段另加 RFFE、综合修复、深度 1／5 Checker 和 I²C 骨架起点，形成二十个任务身份；本轮再增加RW／W1C事件检查器，共二十二个。它们分别使用工业解码加周期模型、固定设计与 UVM Scoreboard、独立参考 Formality，以及事件队列模型、逐位真值表和 I²C 引脚／输出账目；不能沿用 X2P 的“提交 bridge.sv”假设。

[有限任务使用指南](tasks/README.md)连接每个契约的 Spec、可修改材料及运行命令；[任务与研究说明](verification-resources-tasks.md)解释能力边界、正反对照、真实漏检与实际模型结果。`python3 -m environment.artifact_task list` 查询有效入口；`python3 -m verification_resources.production_v5` 提供有限生产、依赖检查和初始化。Registry 是当前证据入口，准入仍要求哈希严格匹配；任务创建时的元数据与历史结果不回填。

此前八份任务的准入与四条分层试次、一条独立反馈试次见[多验证资源阶段报告](task-production-stage-v3.md)。该阶段二十份有限包可严格核对依赖并初始化；[库存](../experiments/task-production-v3/task-inventory.json)分开记录工业准入和模型采样。旧 X2P 的历史准入不因此升级为当前源码准入。

新增 [I²C byte／word 契约](tasks/i2c-write-sink.md)已完成 32 项工业准入、28 项接口检查和各一条实际模型试次。终局／保留分别为1／1和0／0；[研究报告](i2c-sink-evaluation.md)不把两条样本当作难度排名。

## 新资源与新起点分别记录

[多验证资源阶段](task-production-stage-v3.md)新增 RFFE 两个寄存器契约、两个综合修复契约、深度 1／5 Checker，以及两个 I²C 骨架补全起点。前六个改变功能或结构义务，后两个保留原 I²C 功能要求、改变初始工程材料；它们均通过各自工业门禁。该阶段 Registry 记录二十个有限任务身份，不能仅凭目录条目推断模型校准完成。生成、准入、运行机制验收和真实求解结果分别由报告链接证据。

## 寄存器检查器：独立事件判据的新交付形式

新增[RW](../tasks/register_checker_rw_v1/spec.md)与[W1C](../tasks/register_checker_w1c_v1/spec.md)两种契约，使用VCS逐拍检查候选的状态预测与错误报告，不执行串行VIP。两者均完成工业准入及各一条真实原生工具试次，详见[研究与证据](register-checker-evaluation.md)。

寄存器阶段为11个X2P加22个有限任务身份，共33个身份、31个去重功能／结构契约。[当时追加目录](../tasks/artifact-registry-v2.json)引用原目录而不改写历史；当时cli_v2列出22个有限任务，最早CLI仍列此前20个。新任务的reset/test/submit、材料化及Rollout命令见[复现入口](../experiments/register-checker-v1/README.md)。

## SWD：有限双向传输的新工程对象

[SWD读响应规格](../tasks/swd_read_v1/spec.md)要求目标正确识别线复位与请求、捕获载荷并按阶段取得和释放数据线。它完成19项工业准入及一条真实失败轨迹，见[实际证据与限制](swd-read-evaluation.md)。SWD阶段总量为34个任务身份、32个去重功能／结构契约；新增的是一个有限传输契约，不是完整DP。

[该阶段追加目录v3](../tasks/artifact-registry-v3.json)保留旧目录；cli_v3列出23个有限任务。此契约目前为人工审阅样板，production_v7进行严格材料化，不宣称已能自动生成任意SWD任务。

## 功能保持的固定流程结构优化

[位计数预算任务](bitfold-optimization-evaluation.md)新增资源约束，要求完整功能与两类等价通过后，映射单元数不超过22。15项门禁与一条真实回归失败轨迹已完成。当前合计35个身份、33个去重功能／结构契约；[目录v4](../tasks/artifact-registry-v4.json)与cli_v4列出24个有限任务。production_v8只材料化这份经审阅契约，不宣称任意PPA任务生成。
