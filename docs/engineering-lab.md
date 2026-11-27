# 用候选版本组织工程调试

一次测试通过后，Agent 又修改了 RTL，先前的 PASS 还能说明什么？它只能说明**之前那一份源码**通过了对应测试。队列任务的[真实回归案例](queue-family-evaluation.md)表明，区分“当前设计”和“已经测过的设计”是工程环境的一项基本责任。

`engineering-lab-v1` 将已有工具组合为一个独立条件，并在开发反馈中显式关联源码版本。它首先面向 `x2p_queue_three_v1`，不改变该任务的容量、仲裁或终局奖励。该配置已通过[实际九种动作联用验收](../experiments/composed-stage-v1/tools/combined-acceptance.json)：包括编辑后查询旧结果时标为非当前版本，以及提交后的独立评分。另有运行时 29 项、综合 20 项检查。工具可用并不说明 Agent 一定会有效定位和修复，真实行为见[研究报告](composed-environment-evaluation.md)。

## 工具怎样共同支持一次调试

假设 Agent 发现响应退休后，下一笔 APB Setup 比 Spec 晚了一个周期。完整公开测试可以确认这个错误；`inspect` 给出对应的调度需求；`experiment` 选择相关场景或构造少量事务；`observe` 按 `B:0`、`APB_COMPLETE:0` 等事件定位局部窗口。编辑之后，需要用当前版本重新验证，才能判断时序变化是否修复了问题。

这个例子说明工具的职责关系，并非已经观察到的成功模型轨迹。工具可以使用、模型实际调用、相关反馈被送达，以及修改确实修复错误，需要分别从轨迹核查。

| 工具 | 提供的工程证据 | 不代表什么 |
| --- | --- | --- |
| `compile` | 当前 RTL 能否完成独立编译、受控编译诊断 | 不验证事务功能 |
| `synth_check` | 综合流程结果与有限结构性提示 | 不提供 PPA 奖励或完整正确性证明 |
| `test` / `inspect` | 全部公开功能测试；最近一次公开失败的需求级解释 | 不暴露私有评分、不自动重测修改后的源码 |
| `experiment` / `observe` | 指定公开场景或结构化事务的实际接口事件；事件窗口查询 | 不能修改终局测试，也不是内部状态的全量波形访问 |
| `read` / `edit` / `submit` | 阅读契约、修改源码、冻结最终候选 | 提交后不继续利用私有反馈修复 |

自定义事务的延迟字段各有明确参照事件，不能全部理解成“从仿真开始等待多少周期”。具体边界和例子沿用[事件导航 v2](runtime-events-v2.md)。目前不开放任意命令、自建 SV Testbench、内部信号名称或完整日志。

## 反馈与哪个版本有关

执行相关工具后，反馈附带 `candidate_binding`。以下仅为字段示意：

```json
{
  "current_sha256": "当前 bridge.sv 的哈希",
  "result_sha256": "被测试或观察的 bridge.sv 的哈希",
  "is_current": false
}
```

`inspect` 和 `observe` 查询已有记录。编辑后再次查询，旧结果仍可用于理解修改前的行为，但 `is_current=false` 会明确指出它尚未验证当前设计。`compile`、`synth_check`、`test`、`experiment` 实际执行当前候选；`edit` 和 `submit` 返回更新或冻结后的身份。

`is_current=true` 只表示源码版本相同，不表示测试通过或设计正确；仍须同时查看工具状态及验证范围。

这个机制不替 Agent 回退代码，不替它执行遗漏的测试，也不会因为存在旧 PASS 就改变终局奖励。审计器会根据实际源码演变重新计算绑定，不能只相信反馈中的布尔值。

## 独立版本与运行入口

```bash
python3 -m task_families.engineering_lab_v1.generate .local/queue-lab
python3 scripts/tasks.py --package .local/queue-lab \
  quality x2p_queue_three_v1 .local/admission
python3 scripts/tasks.py --package .local/queue-lab \
  rollout x2p_queue_three_v1 -- \
  --admission .local/admission --out .local/lab-rollout \
  --policies test_diagnostic --capabilities engineering-lab-v1 \
  --protocol text-json-atomic-v2 --repeats 1 --limit 1
```

运行前需要配置实际工业工具与模型凭证；不在命令或公开记录中填写密钥。Rollout 会要求源码匹配的任务准入，并执行运行时、综合和综合调度流程的真实机制验收。任何必要验收失败，都不能启动模型试次。

本版总动作预算为 20，公开测试最多 2 次；另有 compile 2 次、synth_check 2 次、inspect 2 次、experiment 3 次、observe 4 次，全部共享总动作上限。尝试和拒绝按对应工具的原规则记账。综合环境属于新的实验条件，不与历史单工具条件合并计算成功率。

[`engineering_lab.py`](../environment/engineering_lab.py)组合既有 Session；[环境生产器](../task_families/engineering_lab_v1/generate.py)绑定升级后的控制器、Prompt 和审计器。历史包和历史配置不会被就地升级。
