# 队列任务族：证据入口

本目录发布第二类有限任务族的来源、工业准入与研究证据。任务从 Task003 派生，改变未退休容量，保留执行等待响应消费的契约；三份包不是三个新协议。原任务和历史研究目录不回改。

[研究结论与限制](../../docs/queue-family-evaluation.md) · [理解契约与验证义务](../../docs/queue-family-production.md) · [生成器与执行方式](../../task_families/queue_v1/README.md) · [事件导航 v2](../../docs/runtime-events-v2.md)

## 先确认生成包是否真的可用

[目录](catalog.json)将契约、Spec、任务元数据、完整源码清单和准入摘要关联。每份 `quality/` 是实际工业门禁的白名单导出，原始私有向量和商业工具日志不在公开仓库。

| 契约 | AW/W/AR 容量 | 合法参考 / 错误对照 | 完整 / 公开 case | 证据 |
| --- | --- | --- | --- | --- |
| single | 1/1/1 | 2 通过 / 12 拒绝 | 23 / 21 | [Spec](single/spec.md) · [义务](single/obligations.json) · [摘要](single/summary.json) |
| three | 3/3/3 | 2 通过 / 14 拒绝 | 23 / 21 | [Spec](three/spec.md) · [义务](three/obligations.json) · [摘要](three/summary.json) |
| readheavy | 1/1/3 | 2 通过 / 13 拒绝 | 23 / 21 | [Spec](readheavy/spec.md) · [义务](readheavy/obligations.json) · [摘要](readheavy/summary.json) |

每份另有 40 项真实机制检查和隔离检查。摘要不仅记录总数，还将每项验证义务与两种参考实际观测到的覆盖项、被拒绝的错误对照关联。覆盖满不表示所有并发交错已被穷尽。

[验证器故障探针](oracle-faults.json)保存同一错误 RTL 在正常／损坏 Scoreboard 下的 0/null 对照，以及合法参考在缺少账本钩子时的 null。它们使用独立副本，不属于模型失败或历史漏检。

## 工程观察能力的实际证据

[48 项工具验收](tools/acceptance.json)检查事件查询、实际错误、观测不干扰判定、权限和预算。[容量反例](tools/capacity-counterexample.json)展示 APB 完成后、B 响应尚未退休时错误接受第四个 AW 的过程。[合法实验窗口](tools/actual-event-navigation.json)来自真实仿真；[历史窗口重放](tools/historical-window-replay.json)则是事后投影，二者都不是 Agent 修复成功的证据。

## 三条真实求解记录

[预定计划](study-plan-v2.json)只启动三条，不替换失败试次；[结构化结果](study-results.json)逐条件保留全部分母、候选、实际反馈和成本。

| 独立条件（每项 n=1） | 私有 / 保留 | 值得核查的行为 | 轨迹与候选 |
| --- | --- | --- | --- |
| single / 基础 E | 0 / 0 | 未调用测试，违反明确的 Setup 调度时序 | [episode-1](episode-1/) |
| three / 基础 E | 1 / 1 | 首次测试失败，修改响应生命周期后通过 | [episode-2](episode-2/) |
| three / 事件实验 | 0 / 0 | 首候选事后公开 PASS，第二次编辑引入回归，后续未修复 | [episode-3](episode-3/) |

最后一条实际调用 3 次命名实验、2 次测试，没有自建事务或 `observe` 查询；一次超预算测试被拒绝。工具存在、默认窗口曝光与主动使用事件索引是不同事实。不能把这些不同条件的三条合成能力成功率，也没有验证首候选的私有正确性。

[精确输入参考核验](input-qualification/summary.json)覆盖本轮四个不同契约—输入组合：两组复用完全相同的已验收输入证据，两组新跑完整 23 case 均通过，新增约 500.9 秒。它发生在求解停止后，不修改模型候选与奖励，不公开原始私有向量。

[v4 交换核对](exchange/validation.json)确认三条独立身份、实际反馈一致性及 artifact 哈希。每条 `exchange/episode-N/` 分开保存求解记录、保留评估与事后分析；`episode-N/` 是审查后的 Policy 证据，原始 API 和商业仿真日志留在可信存储。

## 版本、复现与成本

[研究计划](study-plan-v2.json)在新增模型调用前冻结候选与试次上限；[重建检查](reproduction.json)核对全新生成的清单与冻结包逐字节一致；[源码体积](source-footprint.json)测量副本成本，[成本记录](costs.json)将准入、前置检查与模型执行分开。初期最小容量包曾通过门禁，但正式包随后增加执行标记和错误对照；[开发前身摘要](development-predecessor.json)仅作为过程成本与版本区分，不与正式准入或模型样本混计。

重建需保留 Git 中的基础提交。商业工具、许可配置与私有输入须自行合法提供；重建清单或核对公开哈希不是一次新的仿真。先生成新包，再按[运行说明](../../task_families/queue_v1/README.md)获取与当前源码和工具链匹配的准入。

[交付核对](validation.json)与[文件清单](publication-manifest.json)记录单元检查、来源一致性、链接和本地渲染审查。实际工业证据、模型求解和文档检查各自保留范围，不互相替代。
