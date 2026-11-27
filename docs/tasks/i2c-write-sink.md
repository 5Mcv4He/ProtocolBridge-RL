# I²C 写入：从串行字节到事务内组字

I²C 用 SCL 时钟和 SDA 数据传输字节，接收方在第 9 拍通过 ACK 确认接收。这个任务要求模型将串行数据转换为系统时钟域内的输出事件：不仅要收对数据，还要正确应答，并管理数据属于哪一笔事务。

两份契约都使用单主设备、7 位地址 0x52、100 kHz 写事务、100 MHz 系统时钟和 `i2c_sink.sv`。没有读、重复 START、时钟拉伸、输出反压或事务中复位。完整支持范围以各自 Spec 为准。

| 任务 | 交付行为 | 新增验证义务 |
| --- | --- | --- |
| [i2c_sink_byte_v1](../../tasks/i2c_sink_byte_v1/spec.md) | 每个字节形成一次输出，高 8 位为零 | 位次序、ACK、单拍输出及延迟 |
| [i2c_sink_word_v1](../../tasks/i2c_sink_word_v1/spec.md) | 同一事务内每两个字节组成一个 16 位字 | 高低字节归属、奇数长度事务的残余丢弃 |

例如 `12 34 56 → STOP → AB CD`，word 版本应交付 `1234` 和 `ABCD`，不能把残余 `56` 拼到下一笔中。这个变化增加了事务局部状态，而非仅更换测试随机种子。

## 谁检查什么

工业 I²C VIP 主设备负责发送，Monitor 采样完成事务并执行协议检查。项目另建引脚解码器和输出账目，核对实际字节、每个 ACK、输出内容、数量和时刻。被动 VIP 不代替 DUT 应答；缺失 ACK 的错误实现必须被拒绝。

[32 项质量门禁](../../experiments/i2c-sink-v1/quality.json)验证两种合法位存储结构、功能和时序反例、无效交付及编译错误。首轮生成失败与修订过程保留在[拒绝记录](../../experiments/i2c-sink-v1/quality-rejected-v1.json)。生成器输出仍是候选材料，来源匹配的门禁才授予准入。

模型使用 read/edit/test/submit。真实调用经过 Session v3，公开反馈只有状态、错误类别、候选哈希及测试余额；完整日志、引脚数据、参考和私有输入不返回模型。提交冻结源码并结束求解，终局和保留评估分别保存。人工复现命令属于可信操作者入口，不是额外授予模型的 shell 权限。

## 最小复现路径

需要合法的 VCS 与 I²C VIP 安装及已配置的远程执行环境，见[工具链说明](../toolchain.md)。本任务实际验收使用 VCS O-2018.09-SP2、I²C VIP R-2020.12、UVM 1.1d；其他版本需要重新核验。除既有本机配置外，增加以下两个字段，填写自己的安装位置：

```json
{
  "i2c_vip_setup_root": "/your/dw_vip_setup/i2c-project",
  "i2c_uvm_root": "/your/uvm-1.1d"
}
```

这些字段应合并到忽略的本机配置中，不覆盖已有设置，也不提交个人路径或许可内容。VIP 使用它要求的参考时钟，DUT 使用独立的 100 MHz 时钟；测试台负责两者的对应关系。

先用合法参考确认真实后端，再开始自己的工作区：

```bash
python3 -m verifier.i2c_sink.campaign i2c_sink_byte_v1 \
  tasks/i2c_sink_byte_v1/reference.sv .local/i2c-reference
python3 -m environment.artifact_task reset i2c_sink_byte_v1 .local/i2c-work
# 阅读 spec.md，修改 .local/i2c-work/i2c_sink.sv
python3 -m environment.artifact_task test i2c_sink_byte_v1 \
  .local/i2c-work .local/i2c-public
python3 -m environment.artifact_task submit i2c_sink_byte_v1 \
  .local/i2c-work .local/i2c-submit
```

参考运行应得到 Reward=1；初始空功能模板应被拒绝。公开测试通过不能代替终局结果。输出目录须为新目录，避免覆盖证据。完整门禁通过以下入口重新执行，它会真实编译与仿真所有对照，耗时明显多于一次公开测试：

```bash
python3 -m verifier.i2c_sink.quality_v2 .local/i2c-quality-new
```

## 生成与材料化的区别

[生成器修订 2](../../task_families/i2c_sink_v1/generate_v2.py)装配 Spec、模板、合法与错误实现。它只支持 byte/word 两种明确契约，不是任意协议生成器。材料化入口另外核对准入证据、完整依赖集合及源码身份，再复制可信任务包；reset 只把 Spec、起始交付物和身份放入求解工作区。

```bash
python3 -m task_families.i2c_sink_v1.generate_v2 word .local/i2c-candidate
python3 -m verification_resources.production_v4 produce \
  i2c-write-sink word .local/i2c-package
python3 -m verification_resources.production_v4 reset \
  .local/i2c-package .local/i2c-package-work
```

有限仿真和两种参考结构不构成完整协议或可综合性证明。模拟电气行为、亚稳态、未支持事务和任意输入序列不在本门禁范围内。模型的真实表现、成本与证据用途须结合对应研究记录判断，不能从生成成功或一次 PASS 推导训练收益。
