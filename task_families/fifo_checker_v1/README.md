# FIFO 检查器任务族

把事务身份、容量和生命周期要求变成检查器设计任务。Agent 交付的检查器运行在 VCS 内，可信队列模型逐周期评价误报／漏报；候选不能修改奖励。

```bash
python3 -m task_families.fifo_checker_v1.generate_v2 3 NEW_CANDIDATE_DIR
python3 -m verifier.fifo_checker.quality_v2 NEW_GATE_DIR
python3 -m verification_resources.production_v3 produce fifo-checker depth3 NEW_PACKAGE
```

生成支持深度 1–5，当前工业准入和运行适配只支持 2、3。改变深度后必须重新检查容量、回绕、满队列交换与存储复用后的错误身份，不能只更换数值沿用证据。

[规范与实例](../../tasks/fifo_checker_d3_v1/README.md)、[实际门禁](../../experiments/task-production-v2/checker-quality-v2.json)和[模型研究](../../docs/task-production-stage-v2.md)分别回答要求、证据与经验行为。原 generate.py 与 v1 门禁保留一次真实漏检；当前使用 generate_v2、model_v2、campaign_v2 和 quality_v2。生成器不能自行授予准入。
