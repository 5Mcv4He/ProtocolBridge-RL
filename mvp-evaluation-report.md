# Revision 3 验证报告

日期：2026-11-24。**revision 3 单任务闭环已实现且实际验证。** 这不是完整工业签核。运行源码冻结版本为 `8d55867`，公开证据见 [industrial-v3](experiments/industrial-v3/README.md)。历史 v2 的 128 笔通过仅对应[旧报告](experiments/industrial-v2/evaluation-report.md)。

## 已实现与实际证据

- 在 UTM 内安装 DSH SDK / Runtime 0.2.2rc2、Python 3.10；真实 API 探针返回预期结果。
- 低权限 UID、chroot、mount/PID/IPC namespace、no_new_privs 隔离探针通过。网络仍共享，未宣称完整恶意代码沙箱。
- VCS V-2023.12-SP2 + AMBA SVT R-2020.12 + UVM 1.1d，独立预期内存与实际 APB 内存。
- Spec revision 3 明确半请求、APB 阶段与 AXI 响应阶段复位行为。
- 公开 17 个 case／132 笔计划事务；完整 22 个 case／2868 笔计划事务，包含 26 笔故意复位取消。完整集含四组 256 笔随机流，以及 576 个必要交叉 bin。
- 新增四个错误实现，共 10 个故障对照，全部在实际 VCS 仿真中被检出。

## 验证器开发中发现的问题

取消通知曾被误计为正常完成；APB driver 复位时的 item_done 所有权需要由 driver 自己维护；动态调整 READY 配置曾让背压作用到后续事务。已保存原始失败记录，不能将这些开发阶段结果作为 DUT 缺陷证据。

一次交叉运行虽然 1152 笔功能比对通过，但实际背压与计划不一致，被完整性检查判为 null。这正是需要独立激励有效性检查的原因。最终版本每次仿真固定 READY 模式，按实际引脚合并覆盖；完整回归已通过。原始失效结果见 [bringup.json](experiments/industrial-v3/bringup.json)。

## 正确参考 RTL 的实测结果

| 项目 | 结果 |
|---|---:|
| 独立仿真 case | 22 / 22 通过 |
| 计划事务 | 2868 |
| 正常完成并由 UVM 比对 | 2842 |
| 按计划复位取消 | 26 |
| AXI 完成 | 2842 |
| APB 完成 | 2850（包含 8 笔 APB 已完成、AXI 响应被复位取消） |
| 必要交叉 bin | 576 / 576，缺失 0 |
| 四组随机流 | 每组 256 笔，全部通过 |
| UVM 错误／fatal | 每个参考 case 均为 0 |
| 无外部等待／背压时的延迟 | 请求接受至 Setup 为 1～2 周期；APB 完成至 AXI VALID 为 1 周期 |

延迟统计来自引脚事件；不代表最大吞吐率或综合后频率。参考 RTL 的所有正常事务和中断事务均有账目检查。

## 错误 RTL 的实测结果

控制组使用同一个 Scoreboard 和判据。已知故障优先运行对应场景，在首个确认错误处停止；不是十个错误实现都跑完了全部 22 个 case。选择编号不进入判分逻辑。

| 故障实现 | 实际检出的 case | 分类 | Reward |
|---|---|---|---:|
| bad_address | address_data | transaction_functional_error | 0.0 |
| bad_strobe | write_accumulate | transaction_functional_error | 0.0 |
| bad_error | wait_error | transaction_functional_error | 0.0 |
| bad_wait | wait_error | protocol_timing_error | 0.0 |
| bad_read_data | address_data | transaction_functional_error | 0.0 |
| bad_backpressure | response_backpressure | protocol_timing_error | 0.0 |
| bad_reset_half | reset_aw_only | protocol_timing_error | 0.0 |
| bad_reset_response | reset_b_stall | protocol_timing_error | 0.0 |
| bad_early_read | address_data | transaction_functional_error | 0.0 |
| bad_accept_latency | address_data | protocol_timing_error | 0.0 |

背压不稳定和复位未清响应实际触发商业 AXI VIP 检查，其他缺陷由 UVM 事务比对或任务时序断言检出。不能把手写 10 个故障全被检出推广为所有缺陷均可检出。

## 评分规则与分类探针

终局 1.0 要求全部必要 case 完整通过、事务账目及必要覆盖齐全；确认的编译／协议／功能／周期超时错误给 0.0；基础设施故障、输入无效、墙钟超时或检查不完整给 null。覆盖比例不是奖励。

实际语法错误编译返回 `0.0 / compile_error`；空测试集合返回 `null / infrastructure_error`。评分与计划的 14 项单元检查通过；其中合成日志仅测试解析契约，不作为 EDA 仿真证据。全局周期 watchdog 的独立故障注入尚未实测。

## 真实 Agent 试次

DSH SDK / Runtime 0.2.2rc2、Python 3.10.12 在 UTM 内运行，请求模型 `deepseek-flash`，provider 为 DeepSeek 官方 API。真实动作记录来自 API 响应，由固定工具接口执行；没有脚本代写 Agent 答案。

本次共 10 轮：读取 2 次、被拒绝的动作 2 次、有效编辑 2 次、公开测试 3 次、提交 1 次。最初空模板失败及未读模板而被拒绝的编辑单独保留，不计作生成 RTL 的功能修复。

第一版生成 RTL 在写后读时不能及时接受 AR，公开测试实际报出请求接受超过 16 周期。Agent 自行移除 ARREADY 对旧 `is_write` 状态的依赖，并修正 AW/W 各自独立的 READY 条件。[失败 RTL](experiments/industrial-v3/agent/failed-tested.sv)、[最终 RTL](experiments/industrial-v3/agent/final.sv)与[修复差异](experiments/industrial-v3/agent/repair.diff)可直接核对。

| 阶段 | 实际结果 |
|---|---|
| 修改后公开测试 | 17/17 case；132 planned、124 checked、8 aborted；通过 |
| 独立私有奖励 | 22/22 case；2868 planned、2842 checked、26 aborted；576/576 bins；Reward=1.0 |
| 保留评估 | 同一最终 RTL，另一组冻结输入；22/22 case；2842 checked、26 aborted；通过 |
| 冻结检查 | 通过；源码与 `8d55867` 逐文件一致，奖励与保留评估输入哈希不同且均未改变 |

求解进程在保留评估前停止，评估结果没有用于修改这份提交。完整模型事件、候选、公开反馈、私有向量与仿真日志本地保存；[公开轨迹](experiments/industrial-v3/agent/trace.json)和[证据索引](experiments/industrial-v3/README.md)提供脱敏内容与哈希。

## 复现

先按[运行手册](docs/mvp-running.md)准备有授权的 VCS / AMBA SVT、UTM DSH 和自己的 API key，然后执行：

```bash
bash environment/reproduce.sh .local/reproduction-new
python3 -m verifier.grade experiments/industrial-v3/agent/final.sv .local/replay-new
python3 -m environment.agent .local/agent-new --model deepseek-flash
```

第一条验证参考与故障对照；第二条无需模型 API，重放公开的完整默认回归；第三条发起新的真实试次。原试次私有输入不上传，可信操作者可用保留的 `cases.json`／私有 JSON 精确重放。

## 当前边界

有限的随机流与定向组合不能穷尽无限长等待或所有状态；没有完整 RTL 代码覆盖闭合、复位与所有错误／字节使能组合交叉、最大吞吐率验证、综合或形式证明。当前 UTM 的 VCS/VIP 编译实测约需 8～9 分钟／构建；大规模 RL 试次仍需优化编译隔离、缓存和运行资源。工具安装需求与区别见[工具说明](docs/toolchain.md)。

[架构](docs/architecture.md) · [Agent 与奖励](docs/agent-workflow.md) · [覆盖计划](docs/verification-plan.md) · [复现命令](docs/mvp-running.md)

## 下一步技术差距

- 验证闭合：扩展复位交叉、不同合法微架构的正对照、系统化故障注入，补 DUT 代码覆盖及商业 VIP 覆盖分析。
- 执行隔离：补试次之间的文件隔离、网络限制和不可信 RTL 编译／仿真沙箱。
- 综合／形式：准备有授权的 DC、标准单元库与约束，以及可用的 VC Formal FPV；分别提供真实综合报告和带假设、非空性检查的属性证明。
- RL 评估：预先固定多次独立试次及预算，统计成功率、修复次数、成本和保留集表现。当前一次成功不能证明任务太简单或已经适合训练；尚未更新任何模型参数。

## 完成状态

- **已实现且实测**：v3 Spec／模板、reset/test/submit、主动商业 VIP 与 UVM Scoreboard、定向／随机／事务中复位、必要交叉覆盖、10 个故障检出、UTM 内 DSH 与 API、求解进程隔离探针、真实失败后修复的 Agent 试次、私有 Reward 和保留评估、脱敏证据与复现入口。
- **已实现但未单独实测／全面审计**：全局周期 watchdog 尚缺独立 EDA 故障注入；源码门禁未做完整抗绕过审计；公共安装脚本已在当前 UTM 重跑，但未在另一台干净主机独立重测从零安装。
- **尚未实现**：完整代码／VIP 覆盖闭合、试次之间 OS 文件隔离及完整网络／不可信编译沙箱、综合／形式证明、多次模型成功率评估与 RL 参数训练。
