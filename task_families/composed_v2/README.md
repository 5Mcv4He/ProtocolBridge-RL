# 地址窗口怎样与请求生命周期组合

单事务路由器只需在当前请求上选择目标；有请求队列以后，目标归属必须随着已接受的地址保存，经过仲裁、APB 等待和 AXI 响应背压，直到退休或复位取消。这个生产器复用已有路由与队列组件，生成带新地址窗口的组合契约，研究组件复用能否减少每份任务的专用开发工作。

**当前输出是候选包。** 静态生成成功不代表工业准入，工业正反对照也不自动代表求解环境已经验收。历史组合任务及其证据不变；背景见[既有组合方法](../../docs/composed-task-production.md)。

## 能生成什么

当前域为三个 APB4 目标，每个窗口固定 64 KiB，基址可以按四字节对齐，并可与目标编号呈不同的地址顺序。窗口不得重叠，末端必须低于保留的未映射区。协议仍为 32-bit AXI4-Lite → APB4；AW/W/AR 各有两个未退休名额，采用已有轮询仲裁与单个退休后才能继续执行的 APB 执行器。

例如，窗口从 `0x10004` 开始时，全局地址 `0x20000` 的局部地址应是 `0xfffc`。模型不能用截取低 16 位代替基址相减，也不能在排队后根据当前 AXI 引脚重新选择目标。相邻窗口和非数字顺序的目标编号是合法的另一种布局；它们是组合契约实例，不代表新增协议种类。

生成材料包括 Spec、接口模板、两种合法 RTL 结构、适用错误对照、公开与完整场景、独立地址锚点、验证义务和完整源码清单。生成器保留专业语义：协议驱动和队列账本来自成熟组件，地址判据与组合后的复位义务由本任务族装配。

## 为什么不能只合并两份覆盖表

旧组合义务要求三个目标都经历过复位，但这并不保证每个目标在每个生命周期阶段都被中断。新候选要求 **三个目标 × 六个阶段**：写／读 Setup、写／读 Access、B／R 响应等待，共 18 项交互行为。覆盖根据复位时的真实接口信号与已缓存请求身份记录，场景声明本身不算命中。

每个交互项同时生成针对该目标和阶段的复位错误对照。非页对齐实例另有错误局部地址掩码对照。功能负例必须实际进入仿真并被功能或时序检查拒绝；编译失败、超时或环境错误不算成功检错。两个合法结构必须分别通过全部必要场景与覆盖，才能完成实例功能层验收。

这仍不是完整功能证明。固定容量、单执行器和退休耦合边界没有扩展为任意深度、Burst、ID 或多执行器；新的参数域需要新的适用性分析。

## 从契约生成候选

```json
{
  "task_id": "x2p_composed_example_v2",
  "windows": [[65540, 65536], [2147745804, 65536], [327688, 65536]],
  "purpose": "Non-page-aligned target identity through retirement-held request queues"
}
```

在项目 checkout 中运行，将上面的契约保存为 `contract.json`：

```bash
python3 -m task_families.composed_v2.generate contract.json candidate
python3 -m task_families.composed_v2.execution candidate execution
python3 -m task_families.composed_v2.reset_controls_v3 execution corrected-execution
```

第一步生成完整材料并执行静态检查；第二步装配显式 EDA 环境入口及受源码绑定的控制银行执行路径；第三步修正下述错误对照生成问题。各步骤拒绝覆盖已有目录，失败目录留作调查。修订执行包在合法工具环境中配置私有运行参数后，可以从包根目录运行：

```bash
python3 -m environment.instance_controls controls --domain task003
```

`controls/result.json` 是功能对照层结果，`admitted` 始终为 `false`。它还需要完整证据审计以及匹配该任务域的运行、权限与提交机制验收，才能进入 Agent 任务池。不要把 router-only 的运行准入记录直接用于队列任务。

进一步核查：[契约边界与字节锚点](contract.py)、[生成机制](generate.py)、[交互场景](scenarios.py.in)、[正反对照执行](../../environment/instance_controls.py)、[来源与实际输入审计](../../environment/instance_control_audit.py)。

## 错误对照本身也需要验收

首次候选的源码审查发现：响应等待阶段的六个复位负例先写入 `VALID <= 1`，随后在同一个时序过程里执行正常的 `VALID <= 0`。后一次非阻塞赋值覆盖前一次，预期缺陷实际上未生效。相关工业队列在启动前停止，原候选与计划保留，没有产生错误的工业准入声明。

[控制生成修订 v3](reset_controls_v3.py)将条件性违规赋值放在正常复位赋值之后。它不改变 Spec 或可信功能判据，不把修订候选计作新工程契约。[实际定向仿真](../../experiments/task-space-v1/composition/shifted-controls-v1.json)已经确认：合法实现通过、原失效负例通过、修订负例被协议／时序检查拒绝。随后[两份新契约](../../experiments/task-space-v1/composition/manifest.json)均完成两种合法结构各 44 个完整与 42 个公开 case，每份 38 个错误对照全部被功能或时序检查拒绝，并分别审计 210 条真实仿真及输入记录。两份整项验收耗时约 1071 与 1035 秒；第一份额外包含定向负例资格实验。两者都不能直接继承单事务路由任务的运行准入，尚未进行新组合实例的 Agent 求解。
