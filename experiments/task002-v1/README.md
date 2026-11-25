# Task002 revision1 evidence

- [研究报告](../../docs/task002-evaluation-report.md)：真实验收、9条模型试次、失败原因与结论边界。
- `quality/`：两种正确参考、13错误对照、40机制检查、分类与隔离探针；输入/源码/工具链冻结及原始证据哈希。
- `pilot/`：9条完整统计、实际反馈、全部来源哈希；4条代表性成功/失败轨迹及候选RTL。未展示完整轨迹的试次未从分母删除。

私有向量、商业VIP、部署信息、原始API和仿真日志保留在可信本地，不发布。求解Agent当时只看到受限Spec/RTL/投影反馈，提交后停止；研究侧终局和保留结果不是Agent Observation。

```bash
python3 scripts/export_task_quality.py experiments/task002-v1/quality --verify
```

此命令验证发布文件哈希与汇总一致性，不执行RTL仿真。完整仿真及重新验收命令见任务包；需合法VCS/VIP环境。
