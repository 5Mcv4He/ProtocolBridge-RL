# Task 002 — AXI4-Lite → 三目标 APB4 路由

本任务测量完整地址译码、局部地址转换、单目标选择、响应多路选择及未映射 DECERR。它继续使用单笔未完成事务；不将随机种子的变化视为新任务，也不因功能更多就预先标记为“Hard”。经验难度须由独立模型试次校准。

- [功能契约](spec.md)：端口、三个地址窗口、未映射访问、复位及明确不支持的行为。
- [任务声明](task.json)：参考实现、错误对照、需求标签与已知盲区。
- [初始 RTL](workspace/bridge.sv)：仅端口模板，没有参考实现。
- 验证器：`verifier/task002/`，主动 AXI VIP、三个独立 APB VIP、事务级 UVM Scoreboard。
- 参考结构：普通缓冲状态机与 one-hot 状态／请求直达结构。错误对照包括译码别名、错误目标、广播、地址/响应/等待选择、字节使能、握手、复位及 DECERR 错误。

任务声明不是验收证明。只有匹配当前源码和工具链的 Task Quality Gate 通过，才允许用新增任务入口启动模型。原始验收和模型日志留在可信侧；公开结果按独立版本发布。

```bash
python3 -m environment.task002 reset .local/router-work
python3 -m environment.task002 test .local/router-work .local/router-public
python3 -m environment.task002 submit .local/router-work .local/router-submission
python3 -m environment.task_quality tasks/axil_to_apb4_router_002 .local/router-gate
# 上一步通过后，运行少量新模型试次；仍使用20动作、C/E两次公开测试
python3 -m environment.policy_experiment --task axil_to_apb4_router_002 \
  --admission .local/router-gate --protocol text-json-atomic-v2 \
  --out .local/router-pilot --repeats 3 --limit 9 \
  --max-tokens 600000 --max-seconds 5400
```

完整回归26个case，公开21个case。公开／私有／保留使用相同功能契约。Scoreboard分别核对mapped、unmapped、每个目标的APB完成数及复位取消；全部目标的必要交叉覆盖共1728bin。零APB的未映射请求不能借用“没有协议错误”作为通过依据，必须完成正确DECERR响应。

未证明任意输入下的形式完备性，未做综合、面积或时序签核。隔离沿用已验收的受限动作控制器及独立运行时；不是任意恶意本地代码的安全容器。私有测试不回流求解过程；公开的参考源码仍可能造成模型预训练污染。
