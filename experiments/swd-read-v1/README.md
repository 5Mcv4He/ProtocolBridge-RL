# SWD 有限读响应：证据与复现

本任务把工业 SWD 资源推进到自建有限目标、正反对照和真实 Agent 求解。先读[工程研究报告](../../docs/swd-read-evaluation.md)理解范围，再用本页核对版本与结果。它不是完整 SWD Debug Port。

## 实际证据

- [修订2工业门禁](quality.json)：19项，合法结构6项通过，功能反例8项及初始模板被拒绝，3项无效交付和1项编译错误分类正确。
- [被拒绝的首轮门禁](pre-admission-review.json)：保留带引号文件名引发的编译错误误分类，不回填历史结果。
- [准入挑战](admission-checks.json)：6项遗漏／变更／错误证据被拒绝，记录92份共享依赖和14份任务文件。
- [冻结计划](study-plan.json)、[真实结果](study-results.json)、[行为分析](behavior-analysis.json)、[成本](costs.json)：一条预声明试次，8次有效编辑、4次公开FAIL、终局0与独立保留0。
- [v9交换](exchange/manifest.json)、[实际事件重放](replay-audit.json)、[累计库存](exchange-inventory.json)：140条研究记录／100条已审查轨迹；不表示全部适合训练。

原始模型事件、完整VCS日志、输入及冻结源码保存在可信研究存储。公开交换保留实际工具提案、送达反馈和候选内容；终局训练奖励与保留结果分区存放。没有事后评分或中间候选替换。

## 同一源码重新验收

需要合法安装的 VCS、SWD VIP、UVM，以及符合[通用运行配置](../../docs/toolchain.md)的可信执行后端。配置添加 `swd_vip_setup_root` 与 `swd_uvm_root`；前者为已有SWD VIP开发环境根目录，后者为含 `src` 的UVM根目录。本次实测VCS O-2018.09-SP2、VIP R-2020.12、UVM 1.1d。

`eda_env_script`负责统一工具环境。可选 `swd_prune_derived_builds: true` 只删除本次创建目录的可再生编译产物，保留源文件、输入、结果和原始日志；它不是复用旧评分或编译缓存。每次构建前要求至少512MiB余量。

```bash
python3 -m unittest tests.test_swd_read
python3 -m verifier.swd_read.quality .local/swd-quality-new
python3 -m verification_resources.production_v7 materialize dp0-latched .local/swd-package
python3 -m verification_resources.production_v7 check .local/swd-package
```

门禁命令实际重新运行VCS；材料化与check只核对已准入源码／证据，不执行新的RTL仿真。不得覆盖本页冻结证据或机械修改哈希来让新源码取得旧准入。

## 使用受控任务入口

```bash
python3 -m environment.artifact_task.cli_v3 reset swd_read_v1 .local/swd-work
# 编辑 .local/swd-work/target.sv
python3 -m environment.artifact_task.cli_v3 test swd_read_v1 .local/swd-work .local/swd-public
python3 -m environment.artifact_task.cli_v3 submit swd_read_v1 .local/swd-work .local/swd-submit
```

这些是可信操作者的复现命令，不是提供给模型的任意命令接口。真正试次使用只暴露read/edit/test/submit的已验收原生worker；必须在独立结果目录使用对应计划：

```bash
python3 -m environment.native_tools.run_v5 \
  experiments/swd-read-v1/study-plan.json swd-read-r1 .local/swd-reproduction
python3 -m scripts.check_native_replay_v3 .local/swd-reproduction \
  --out .local/swd-reproduction-audit.json
```

新运行是新样本，不是覆盖原轨迹或重现相同模型随机过程。管理员入口、凭据与API Key通过可信本机配置提供，不写入公开计划或任务材料。无权限或来源不匹配时应停止，不降低边界。保留评估在求解停止后单独运行，不能用于替模型选择更好的版本。
