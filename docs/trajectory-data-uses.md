# 从研究记录到有依据的数据用途

一份最终正确的 RTL 可以作为实现示范候选，但不能说明模型经历过有效调试。反过来，一条失败轨迹可能清楚记录了误判、无效编辑或提交决策，仍有研究价值。本页说明怎样从已有证据识别这些用途，避免把所有 Reward=1 或所有可导出的记录视为同一种训练数据。

本次规则针对[冻结的历史 132 条记录](../experiments/task-production-v3/exchange-inventory.json)，其中 92 条具有完整工具轨迹，其余 40 条只有结果记录。新原生接口的五条试次使用独立 v9 交换，尚未纳入这个历史筛选分母。没有使用保留评估或事后候选测试来挑选记录。

## 什么证据允许进入哪一类候选

[用途规则 v1](../research/trajectory_use_policy_v1.json)先校验库存与制品哈希，沿实际执行的编辑追踪候选身份，再结合模型真正收到的公开反馈判断。它不修改原 Reward，也不重新评定功能正确性。

| 用途候选 | 必须具备的证据 | 本次数量 |
| --- | --- | ---: |
| 正确实现示范待审查 | 完整轨迹、有效提交、终局 1、无已知失效判据或绑定问题 | 30 |
| 多轮修复示范待审查 | 上项条件，且送达 FAIL → 不同源码的有效编辑 → 同一最终版本公开 PASS | 15 |
| 失败反馈行为分析 | 实际收到失败反馈；不要求最终成功 | 60 |
| 交互失败分析 | 动作拒绝或协议错误记录；部分仅有摘要证据 | 54 |
| 旧判据研究留存 | 已确认被取代的 UART 验证器记录 | 8 |

这些用途允许重叠，不能相加成“训练样本总数”。30 条实现候选只有 **29 份不同的最终源码**，相同源码的多条交互不能当作同等数量的新工程实现。15 条修复轨迹包含 17 对可核查的失败到通过关系，其中 9 对使用显式源码哈希，8 对依靠完整有序编辑与测试重建身份；两种证据强度分别记录。

一个具体判断例子：模型在候选 A 收到 FAIL，编辑得到 B 并收到 PASS，最后又编辑并提交 C。即使 C 的终局正确，也不能把 B 的 PASS 作为“C 已经公开复验”的证据。规则要求修复关系的通过版本与最终提交一致。没有测试过的候选保持未知，不从终局结果反推每次编辑都正确。

[机器可读筛选结果](../experiments/task-production-v4/historical-data-use-candidates.json)逐条保留 episode 身份、候选哈希、判据、缺失信息与用途标签。8 条旧 UART 记录仍保留原始奖励，但不进入实现或修复示范候选；这不是删除失败，也不是把旧奖励回填成新奖励。

## 边界：候选清单不是训练效果证明

筛选回答的是“这份材料有何可核查的用途”，不是“训练它一定有收益”。还需要专业复审、重复度控制、目标模型与训练方法匹配。公开任务和参考可能已有污染，不能宣称长期未见评估。历史验收也不自动等于当前源码可以启动同一任务，实际运行仍需严格准入。

实现只读取 `training/rollouts.jsonl` 与其引用制品，不打开 evaluation 或 offline 分区。七项针对性测试覆盖送达条件、同源码重复、旧 PASS 绑定、新版本变更、null、失效判据与保留／事后结果不影响选择。费用或原始采样字段缺失时仍保持缺失。

## 如何复用这次分析

需要完整的历史交换输入；早期 v2 导出需从可信原始记录重建，只有公开结果摘要时不能补造工具轨迹。

```bash
python3 -m research.trajectory_uses \
  --inventory experiments/task-production-v3/exchange-inventory.json \
  --v2-manifest /path/to/reconstructed-v2/manifest.json \
  --out /path/to/new-use-candidates.json
python3 -m unittest discover -s tests -p test_trajectory_uses.py
```

分析工具使用 Python 3.10 或更新版本。当前用途策略绑定指定历史库存和旧判据说明；库存变化时先复审并建立新策略，不能无条件扩大排除范围或继承标签。

对下一批生产，当前证据支持先补充“有有效交付、有实际反馈、有再次验证”的专业任务轨迹，而不是只提高总记录数。新原生试次提示提交闭环仍有缺口，RFFE 又显示有效编辑之后的串行功能问题；这两类问题应分别记录和研究，不能都归为模型不会写 RTL。

## 原生轨迹的独立用途审查

后续9条原生工程试次采用[新规则](../research/native_trajectory_uses.py)与[独立清单](../experiments/task-production-v4/native-use-review/policy.json)，不改写历史132条的选择结果。新规则交叉核对实际模型收取反馈的证据；仅在测试确认完整功能之后，又对另一编辑版本实际确认功能失败时，标记“已验证功能回归”。因此结构优化中“功能正确但资源超额”的FAIL不会与功能FAIL混为同类。

[结果](../experiments/task-production-v4/native-use-review/results.json)含2条实现示范待审查候选、3条实际失败反馈分析轨迹与1条功能回归轨迹，类别可重叠，没有新增成功多轮修复示范。规则不读取保留分区、私有评分或离线候选测量。5项单元检查覆盖反馈收取一致性、缺少功能测量、未测试修改及保留结果不影响选择。

```bash
python3 -m research.native_trajectory_uses \
  experiments/task-production-v4/native-use-review/policy.json \
  .local/new-native-use-review.json
python3 -m unittest tests.test_native_trajectory_uses
```

这组用途清单为[下一轮采样选择](task-production-stage-v4.md#成本与下一轮选择)提供证据，仍需要工程复审；不能把导出、审计或规则匹配等同于训练有效性。
