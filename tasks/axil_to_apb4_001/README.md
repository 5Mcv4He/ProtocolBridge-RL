# 任务 001：AXI4-Lite → APB4

revision 3，单时钟、32-bit、单笔未完成事务。支持 AW/W 独立到达、字节使能、等待、错误、响应背压和事务中复位；不支持并发读写、burst 或跨时钟。

- [精确 Spec](spec.md)与[初始 RTL](workspace/bridge.sv)
- [功能、边界、随机与复位验证计划](../../docs/verification-plan.md)
- [UVM Scoreboard 和系统框图](../../docs/architecture.md)
- [真实 Agent、公开／私有测试与奖励](../../docs/agent-workflow.md)
- [reset/test/submit 与复现命令](../../docs/mvp-running.md)
- [实际验收报告](../../mvp-evaluation-report.md)

版本改变后需重新跑正反对照和真实试次。旧版本的 PASS 不能作为当前版本验收。
