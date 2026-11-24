# Revision 3 验证报告

日期：2026-11-24。参考与错误对照验收已完成；**UTM 真实 Agent 试次进行中，终局结果待回填**。历史 v2 的 128 笔通过仅对应[旧报告](experiments/industrial-v2/evaluation-report.md)。

## 已实现与实际证据

- 在 UTM 内安装 DSH SDK / Runtime 0.2.2rc2、Python 3.10；真实 API 探针返回预期结果。
- 低权限 UID、chroot、mount/PID/IPC namespace、no_new_privs 隔离探针通过。网络仍共享，未宣称完整恶意代码沙箱。
- VCS V-2023.12-SP2 + AMBA SVT R-2020.12 + UVM 1.1d，独立预期内存与实际 APB 内存。
- Spec revision 3 明确半请求、APB 阶段与 AXI 响应阶段复位行为。
- 公开 17 个 case／132 笔计划事务；完整 22 个 case／2868 笔计划事务，包含 26 笔故意复位取消。完整集含四组 256 笔随机流，以及 576 个必要交叉 bin。
- 新增四个错误实现，共 10 个故障对照，全部在实际 VCS 仿真中被检出。

## 验证器开发中发现的问题

取消通知曾被误计为正常完成；APB driver 复位时的 item_done 所有权需要由 driver 自己维护；动态调整 READY 配置曾让背压作用到后续事务。已保存原始失败记录，不能将这些开发阶段结果作为 DUT 缺陷证据。

一次交叉运行虽然 1152 笔功能比对通过，但实际背压与计划不一致，被完整性检查判为 null。这正是需要独立激励有效性检查的原因。当前改为每次仿真固定 READY 模式，再按实际引脚合并覆盖。

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

DSH SDK / Runtime 0.2.2rc2 在 UTM 内运行，请求模型 `deepseek-flash`，provider 为 DeepSeek 官方 API。当前试次已经实际读取任务、编写 RTL 并调用公开测试。第一版生成 RTL 在写后读时不能及时接受 AR，公开测试报出请求接受超过 16 周期；Agent 随后自行调整 ARREADY 及 AW/W 独立接收条件。最终公开测试、私有奖励及保留评估结果完成后回填，不沿用 v2 Reward。最初的空模板失败和两次未先读模板而被拒绝的编辑另行保留，不计作生成 RTL 的功能修复。

## 当前边界

有限的随机流与定向组合不能穷尽无限长等待或所有状态；没有完整 RTL 代码覆盖闭合、复位与所有错误／字节使能组合交叉、最大吞吐率验证、综合或形式证明。当前 UTM 的 VCS/VIP 编译实测约需 8～9 分钟／构建；大规模 RL 试次仍需优化编译隔离、缓存和运行资源。工具安装需求与区别见[工具说明](docs/toolchain.md)。

[架构](docs/architecture.md) · [Agent 与奖励](docs/agent-workflow.md) · [覆盖计划](docs/verification-plan.md) · [复现命令](docs/mvp-running.md)
