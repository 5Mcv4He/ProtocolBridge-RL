# 三目标路由任务族 v1

本任务族研究一件有限的事：能否从已验收的 Task002 方法自动产生**规格、实现对照、独立验证和执行入口一致**的新地址契约，并逐份验收。窗口变化是参数化任务实例，不代表新增协议或三种独立工程能力。

[为什么需要任务族、地址实例与生产流程](../../docs/task-family-production.md)

## 生产边界

三个目标和单笔未完成事务保持固定。首批只接受 configurations.json 中经审阅的三种契约：紧凑稀疏窗口、非二次幂且目标编号不按地址排序的窗口、相邻窗口。任意参数、目标数扩展和队列组合均不属于 v1。

生成器以明确 Git 提交为基础，产出独立的 **task capsule（可执行任务源码包）**。包内有新 Task ID、Spec、初始 RTL、两种参考、14 个错误对照、VIP/UVM 后端、场景、Policy/Session、质量门禁和统一 CLI。`task002` 内部模块名表示复用的后端位置；包中的新 Task ID 才是实验身份。原仓库 Task001–004 不被重写。

这是一种保守的源码特化：当前运行器对任务有固定分派，因此复用一个完整、隔离的执行包，而不是立即重构为动态插件平台。代价是源码副本与较宽的冻结范围。不同包不能共用未经哈希校验的编译产物或准入证据。

## 如何生成和使用

生成器需要本地 Git 历史中存在其固定的基础提交；浅克隆缺少该对象时需先取回历史。只对可信生成目录使用 `--package`，源码哈希核对不等于可以安全执行任意外来代码包。

从项目根目录运行：

```bash
python3 task_families/router_v1/generate.py x2p_router_irregular_v1 .local/router-irregular
python3 scripts/tasks.py --package .local/router-irregular list
python3 scripts/tasks.py --package .local/router-irregular reset x2p_router_irregular_v1 .local/work
```

`--package` 检查完整源码清单后委派至包内既有 CLI；后续相对路径以包为工作目录。编辑包内 `.local/work/bridge.sv` 后可调用相同的 `test`、`submit`、`quality`、`rollout` 子命令。可信配置通过绝对路径 `PB_CONFIG` 指定，或使用包内忽略的 `.local/config.json`。配置、API 凭据与商业资源不会由生成器复制。

工业门禁在已配置的可信 Linux 执行端运行，因为它还要实际检查当地的隔离边界：

```bash
python3 scripts/tasks.py --package .local/router-irregular quality x2p_router_irregular_v1 .local/gate
```

通过后，控制端使用同一源码包和该门禁的 `result.json`、`freeze.json`，并通过自己的 SSH 后端配置启动模型试次。完整原始证据留在可信存储；编译产物不随源码包搬运：

```bash
python3 scripts/tasks.py --package .local/router-irregular rollout x2p_router_irregular_v1 -- \
  --admission .local/gate --out .local/pilot --policies test_diagnostic \
  --protocol text-json-atomic-v2 --repeats 1 --limit 1 \
  --max-tokens 150000 --max-seconds 1800
```

生成端、执行端和控制端可以位于不同合法工具环境，但必须使用相同的包内源码及匹配的工具链声明。上述命令不替代[基础部署前置条件](../../docs/mvp-running.md)。生成过程先执行包内单元检查；检查失败保留候选目录并停止。生成不会自动授予准入；正式 rollout 必须有当前包与工具链匹配的通过证据。不要修改生成目录后手工更新哈希；修正生成方法，生成新目录并重新验收。

## 防止两个错误互相认可

参考解码采用上界不包含的比较，SV Scoreboard 采用包含上界的区间，刺激端用偏移/长度分类。三者只共享参数事实，不共享 RTL 解码函数。刺激不仅检查窗口外边界，也在窗口内部的二进制偏移进位处执行读写；一个专门错误对照会丢失局部地址 bit 12。此外，手工审阅的 oracle_checks.json 固定端点、相邻边界、非二次幂和高位地址的期望 lane/offset；每次仿真须确认该独立锚点检查实际执行，否则返回环境错误，不给候选数值奖励。

这降低共同错误风险，但不是规格一致性或穷尽输入的形式证明。规格表、生成代码、语义锚点仍需工程审查；每个包还必须实际证明合法实现可接受、错误对照可拒绝。

[能力及复用范围](capabilities.json) · [参数契约](configurations.json) · [生成器](generate.py) · [独立语义锚点](oracle_checks.json)
