# 多任务入口与准入

四个Task定义共用[任务目录](../tasks/registry.json)与[元数据Schema](../tasks/registry.schema.json)。目录描述工程能力、协议、版本、Spec/初始RTL、验证后端、reset/test/submit接口、Policy和Reward契约；它不通过“status=ready”授予评测权限，也不把换随机种子计为新任务。

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

这个基础目录负责统一管理与调用；自动生产由独立的[有限路由任务族](task-family-production.md)承担。增加一个Task需要独立契约、实现/错误对照、实际验证、明确版本与人类README。更新目录后仍须在控制器支持的任务集合中显式登记，避免任意元数据动态扩大求解权限。

验证目录和CLI：`python3 scripts/test_task_catalog.py`。这组测试不消耗VCS许可证；真正的RTL验收使用上面的quality命令。`quality`对001调用原有正反对照，对002/003/004执行新门禁；两者的历史验收范围不能混称。

## 生成任务怎样进入同一个执行路径

[路由任务族 v1](../task_families/router_v1/README.md)从 Task002 复用三目标、单事务的协议与验证基础，生成不同地址窗口契约。每份候选拥有自己的 Registry、Spec、验证后端和源码清单；正式 Rollout 仍需该包及工具链匹配的工业准入证据。原有四任务目录和历史结果不变。

通过 `python3 scripts/tasks.py --package PACKAGE ...` 可使用同样的 list/reset/test/submit/quality/rollout 操作。相对工作路径以包为基准。参数化实例不等于独立工程能力，包清单核对也不等于质量验收；生成、准入和求解的区别见[生产方法](task-family-production.md)。

## 任务契约与研究元数据分开更新

[当前任务研究索引](../experiments/engineering-stage-research-index.json)（[上一阶段索引](../experiments/task-research-index.json)保留）将每个Task的能力、协议、验证后端、版本、污染风险与各次真实实验关联，提供逐Policy样本量、0/1/null、反馈曝光、Token、耗时和来源哈希。由`scripts/research_index.py`从已审查证据生成，不合并独立生成与修复，也不授予执行准入。每次有新结果更新研究索引，保持冻结Spec/任务包不变。

当前实测：[001批量研究](batch-evaluation-report.md)、[002路由](task002-evaluation-report.md)、[003独立生成](task003-evaluation-report.md)、[003同起点修复](task003-repair-report.md)、[003工程工具对照](engineering-tools-evaluation.md)、[004执行/响应解耦](task004-evaluation-report.md)。当前研究报告由此固定索引链接；历史冻结任务包不为追加结果回改。
