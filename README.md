# ProtocolBridge-RL

用真实 RTL 仿真和工业协议 VIP，为编程 Agent 提供可复现的协议转换任务及程序化奖励。

当前交付一个 **AXI4-Lite → APB4** 任务：单时钟、32-bit、单笔未完成事务。Agent 读取 Spec、修改 RTL、调用公开测试并提交；VCS 中的主动 AXI/APB VIP 与 UVM Scoreboard 执行验证。Python 负责调度和 Reward 封装，不承担功能比对。

## 已验证的结果

| 项目 | 实测结果 |
|---|---|
| 正确参考 RTL | 128 笔 AXI/APB 事务全部匹配，UVM 零错误 |
| 六个错误 RTL | 地址、WSTRB、PSLVERR、PREADY、读数据、背压稳定性错误全部检出 |
| 商业 VIP 检查 | 故障注入实际触发 AXI/APB VIP 协议错误 |
| 真实 Agent 试次 | DeepSeek Harness；公开 32 笔、独立终局 128 笔通过；Reward=1.0 |
| 关键时序覆盖 | AW 先到／W 先到／同时到达均命中；602 个背压周期、202 个 APB 等待周期、8 次事务间复位 |

这些是有限测试集合的结果，不是形式正确性证明，也不是模型成功率统计。Agent 在本次试次中测试前编辑了两次，随后一次公开测试通过；没有把空模板失败包装成设计修复能力。

[完整评估报告](mvp-evaluation-report.md) · [公开验收证据](experiments/industrial-v2/README.md) · [任务 Spec](tasks/axil_to_apb4_001/spec.md)

## 运行

需要自行准备有授权的 VCS / AMBA SVT 环境，并配置 SSH。已实测 VCS V-2023.12-SP2、AMBA SVT R-2020.12。仓库不包含商业 VIP、许可证或密钥。

先按[环境配置与运行说明](docs/mvp-running.md)完成配置，然后在仓库根目录执行：

```bash
# 参考实现及六个错误实现的回归
bash environment/reproduce.sh .local/reproduction-001

# 配置 DeepSeek Harness Python 和 API key 后，增加真实 Agent 试次
bash environment/reproduce.sh .local/reproduction-002 --agent
```

也可单独调用 `python3 -m environment.reset`、`environment.test`、`environment.submit`；具体参数见运行说明。模型 API 调用消耗用户自己的额度。

## 交付内容

- `tasks/`：Spec、初始 RTL 和任务元数据。
- `environment/`：reset/test/submit、受限工具接口和 DeepSeek Harness。
- `verifier/v2/`：当前唯一的主动 VIP／UVM 验证实现。
- `fixtures/`：正确参考与六个故障实现。
- `experiments/industrial-v2/`：结果、精简工具轨迹、最终 RTL、事件和证据哈希。
- `scripts/`：脱敏证据导出；`docs/`：复现说明及研究资料。

UVM Scoreboard 通过 analysis port 接收两端 VIP monitor 事务，并与计划请求和独立期望内存状态比较。最终评分在新的仿真目录执行；编译产物只有在代码及验证输入哈希一致时才允许复用。

## 边界

尚未实现 OS 安全隔离、安全私有测试、事务中复位覆盖、完整覆盖闭合、综合／形式验证或模型训练。参考答案和测试生成器公开，因此本仓库定位为开放的任务环境基线，不是防泄漏的隐藏评测集。

关键初始化失败、缺失背压覆盖及 Harness 格式失败均以 null 记录，详见报告；完整原始日志与模型响应本地保留，不随仓库发布。

[原研究设计](docs/research-design.md) · [VIP 资源盘点](docs/vip-inventory-r2020.12.md) · [早期 VIP 审计](docs/vip-audit-2026-11-24.md)

研究资料描述长期方向和当时的证据状态；当前实现与验收状态以本页和评估报告为准。
