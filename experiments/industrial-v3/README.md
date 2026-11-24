# Revision 3：公开验收证据

2026-11-24。运行源码冻结版本：[8d55867](https://github.com/5Mcv4He/ProtocolBridge-RL/commit/8d55867)。已逐文件核对真实试次的 `freeze.json` 与该提交一致。

| 验证 | 实测结果 |
|---|---|
| 正确参考 | 22 个 case 全过；2868 planned、2842 checked、26 aborted；576/576 cross bins |
| 错误对照 | 10 个全部检出；每个在确认错误处停止 |
| 真实 UTM DSH | 10 轮动作，2 次有效编辑；生成 RTL 的公开失败后自行修复 |
| 最终公开测试 | 17 case；132 planned、124 checked、8 aborted；通过 |
| 私有奖励 | 22 case；2868 planned、2842 checked、26 aborted；Reward=1.0 |
| 保留评估 | 同一提交、另一组冻结输入；22 case 通过；不反馈模型 |

## 怎样看证据

- [总清单](manifest.json)、[工具版本](toolchain.json)、[控制组结果](controls-summary.json)。
- [Agent 结果](agent/result.json)、[工具轨迹](agent/trace.json)、[冻结文件哈希](agent/freeze.json)、[真实 Harness 事件哈希与 worker 身份](agent/harness-provenance.json)。
- [实际失败的生成 RTL](agent/failed-tested.sv)、[最终提交](agent/final.sv)、[自主修复差异](agent/repair.diff)。
- [首次生成 RTL 的公开失败](agent/public-06/result.json)、[修改后公开通过](agent/public-08/result.json)、[私有终局验证](agent/final-grade/result.json)、[保留评估](agent/reserved-evaluation/result.json)。
- [UTM API 探针](utm-api-probe.json)、[隔离探针](isolation-probe.json)。
- [开发阶段失效结果及原因](bringup.json)：保留原始 null，修复分类后用新的真实仿真记录确认错误，未改写旧结果。
- [编译错误探针](classification-probes/compile-error.json)与[故意错误的源码](classification-probes/compile-error.sv)；[空测试集探针](classification-probes/empty-suite.json)应为 null。

`planned` 是计划数量；失败用例可能提前停止，不能把全部计划事务当作已完成。`checked`、中断账目和实际执行的 case 见结果文件。成功结果要求完整执行，错误对照只需足够证据确认违反 Spec。

## 发布边界与复现

这里不含商业 VIP、许可、原始厂商日志、完整私有向量或 API 密钥。原始仿真日志／向量在本地保存，通过 `evidence-sha256.json` 关联；完整模型响应及轨迹也保留本地，公开精简版本和哈希。仅导出一份有代表性的失败候选和最终提交，不上传全部过程目录。

控制组结果由完整参考运行与定向错误运行汇总；所有原始日志已用最终评分器重解析核对。统一回归入口为 `bash environment/reproduce.sh NEW_OUTPUT`：参考跑完整集，错误实现优先跑针对其故障的场景，遇到确认错误停止。新 Agent 可用 `python3 -m environment.agent NEW_OUTPUT`；固定 RTL 重放不需要模型 API。详见[运行手册](../../docs/mvp-running.md)。

公开默认回归可精确重生成；原私有 episode 需可信操作者使用保存的私有向量重放。再次调用模型可能产生不同代码；这份记录不是模型成功率统计。
