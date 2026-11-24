# 标准基线：001 X2P（AXI4-Lite → APB4）

当前唯一标准基线为 revision 3，单时钟、32-bit、单笔未完成事务。支持 AW/W 独立到达、字节使能、等待、错误、响应背压和事务中复位；不支持并发读写、burst 或跨时钟。

- [精确 Spec](spec.md)与[初始 RTL](workspace/bridge.sv)
- [功能、边界、随机与复位验证计划](../../docs/verification-plan.md)
- [UVM Scoreboard 和系统框图](../../docs/architecture.md)
- [真实 Agent、公开／私有测试与奖励](../../docs/agent-workflow.md)
- [A／C／E 信息与反馈策略对照](../../docs/observation-policy.md)
- [reset/test/submit 与复现命令](../../docs/mvp-running.md)
- [实际验收报告](../../mvp-evaluation-report.md)

版本改变后需重新跑正反对照和真实试次。旧版本的 PASS 不能作为当前版本验收。

## 基线维护约定

旧 128 笔版本已废弃，当前树不保留旧源码、旧向量或旧交付目录。[baseline.json](baseline.json)固定运行文件哈希、已验证核心文件、公开证据和验收门槛。`python3 -m environment.check_baseline` 检查一致性，`bash environment/reproduce.sh NEW_OUTPUT` 执行真实回归。

任务／评分语义变更必须先重新完成正确实现、故障对照及真实 Agent 试次的验收，再更新基线清单和人类文档。纯文档与未参与执行的废弃文件清理无需伪造或改写旧试次：原始 `freeze.json` 保持不变，按记录的 Git 提交审计；当前基线另行锁定仍在执行的核心文件。

新增任务沿用[固定文档入口](../../docs/README.md)，说明 Spec、结构图、Agent 权限、公开／私有测试、奖励、复用命令、实际证据和未完成边界。
