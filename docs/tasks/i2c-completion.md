# 在已知协议骨架中补全数据交付

先前两条 I²C 模型试次都遇到 ACK 时序问题。这使我们难以判断：模型真正困难的是串行总线时序，还是事务内的组字状态？本任务提供已经验证的接收、地址识别与 ACK 骨架，把待完成部分收敛到数据交付，同时继续检查全部总线行为。

这不是放松原有评分，也不是向模型提供完整答案。起始文件没有交付实现，没有 `half`、首字节寄存器或对应的生命周期处理。`BYTE_ACCEPTED` 标记指出完整字节出现的位置，START、STOP 与复位处提供插入点。允许修改整个文件，但修改协议骨架引入的回归仍会失败。

| 实例 | 需要补全什么 | 与原任务的关系 |
| --- | --- | --- |
| [byte](../../tasks/i2c_completion_byte_v1/spec.md) | 每个字节转为一次单周期事件，高八位清零 | 同一字节交付契约，初始材料改变 |
| [word](../../tasks/i2c_completion_word_v1/spec.md) | 事务内两个字节组成一字，STOP 丢弃残余半字 | 同一组字契约，需维护局部状态 |

例如一笔事务只有一个字节，下一笔有两个字节：word 版本只能交付后一笔组成的字，不能跨 STOP 拼接。[原有示意图与实验背景](../i2c-sink-evaluation.md)解释了这项义务。

## 骨架改变，独立判据不变

新适配层调用已准入的 I²C VIP、独立引脚解码与输出账目检查，并记录底层契约身份。旧任务和旧门禁保持不变。新初始材料、合法完成方式及功能／时序回归另行验收；不能仅凭骨架来源宣称新任务已经可采样。

[18 项工业门禁](../../experiments/task-production-v3/i2c-completion-quality-v1.json)已完成：两种合法实现通过三个阶段，缺少交付、ACK 回归、跨 STOP 半字残留与字节序错误均得到功能或时序拒绝。模型校准尚待完成。后续结果必须与旧空模板任务分开统计。即便观察到新起点更容易完成，少量样本也不能证明骨架普遍提高能力。

```bash
python3 -m task_families.i2c_completion_v1.generate word .local/i2c-completion-candidate
python3 -m verifier.i2c_completion.quality .local/i2c-completion-gate-new
```

工具依赖与本地配置沿用 [I²C 运行指南](i2c-write-sink.md)。[骨架生成器](../../task_families/i2c_completion_v1/generate.py)负责删除被考察的交付状态；[适配层](../../verifier/i2c_completion/campaign.py)负责新任务身份与旧功能判据的绑定。生成成功不等于准入，准入通过也不等于已证明训练价值。
