# 用真实串行事务验收有限 RFFE 寄存器

RFFE 常用于射频前端的寄存器控制。本任务只取一个明确的数字角色：单主设备访问一个从设备的 16 个字节寄存器。Agent 实现串行接收、读回和总线方向切换；可信侧同时检查协议和寄存器内容。**帧合法并不说明读到了正确地址的数据。**

当前 RW 与 W1C 两份契约已经完成 [33 项工业门禁](../../experiments/task-production-v3/rffe-quality-v2.json)。生成、准入和模型校准是不同状态；模型结果与当前运行入口的状态由阶段报告另行记录，不从门禁通过推断。

## 两个实例改变了什么

| 契约 | 设备状态规则 | 新的判断义务 |
| --- | --- | --- |
| [RW](../../tasks/rffe_register_rw_v1/spec.md) | 复位为 0，写入覆盖选中寄存器 | 地址归属、覆盖写入、其他地址保持 |
| [W1C](../../tasks/rffe_register_w1c_v1/spec.md) | 复位为 255，写 1 清位、写 0 保持 | 每个位的清除／保持、重复写、复位恢复 |

例如 W1C 中旧值 `0xFF`、写数据 `0x42`，结果应为 `0xBD`；再写一次 `0x42` 应保持 `0xBD`。这是规格示例，不是模型轨迹。

两份契约共享 Register Read/Write 的传输规则、USID=1、地址 0–15、1 MHz SCLK、500 MHz 系统时钟及空闲复位。普通读模式固定为 VIP `sREAD=0`，不支持同步读扩展、半速读、扩展命令或多主设备。完整边界见各自 Spec；这不是完整 RFFE 控制器或电气认证。

## 三层检查怎样互相约束

VIP 主设备产生真实命令，VIP Monitor 记录请求和读响应。一个独立引脚解码器重新检查命令、数据、奇校验和 Bus Park（驱动 0 后及时释放总线）。Python 寄存器模型则在仿真前计算每次读应返回的值；W1C 使用逐位真值表，而不是引用参考 RTL 的表达式。

必须同时完成全部 224 个物理帧、128 次读回及一次空闲复位。事务数量和地址／数据对应关系也要一致。VIP 的通用存储预测不理解设备专有的 W1C 与外部复位，因此只对该地址范围屏蔽其**存储值预测**，协议检查继续开启；设备状态由独立模型接管。

开发时曾出现“引脚检查通过、VIP 报奇偶校验错误”的分歧。门禁返回 null 并停止，随后查明 VIP 在随机选择未限定的同步读模式。明确模式后，**同一候选、同一输入**通过；没有屏蔽奇偶校验错误。[复验记录](../../experiments/task-production-v3/rffe-configuration-review.json)说明为什么验证器的配置也属于任务契约。

两种合法实现仅在位存储方式上不同，仍共享部分控制逻辑。错误对照覆盖无读驱动、读写地址错配、数据翻转、校验、Bus Park、复位和错误更新规则。有限反例与完整活动检查降低共同错误风险，不能证明验证器完备。

## 怎样生成与重新验收

需要合法安装的 VCS、RFFE VIP 和对应 UVM。已实测版本为 VCS O-2018.09-SP2、VIP R-2020.12、UVM 1.1d。仅在忽略的本地配置中声明安装入口：

```json
{
  "rffe_vip_setup_root": "/your/dw_vip_setup/rffe-project",
  "rffe_uvm_root": "/your/uvm-1.1d"
}
```

沿用通用远程配置和管理员提供的环境入口，不在任务内保存机器或许可信息。以下目录均应是全新目录：

```bash
# 生成候选材料，不自动授予准入
python3 -m task_families.rffe_register_v1.generate w1c .local/rffe-candidate
# 重做完整正反对照，成功条件为 accepted=true
python3 -m verifier.rffe_register.quality .local/rffe-gate-new
# 单独运行参考的公开检查
python3 -m verifier.rffe_register.campaign rffe_register_w1c_v1 \
  tasks/rffe_register_w1c_v1/reference.sv .local/rffe-reference-new
```

[生成器](../../task_families/rffe_register_v1/generate.py)、[独立模型](../../verifier/rffe_register/corpus.py)、[测试台](../../verifier/rffe_register/tb.sv)与[准入检查](../../task_families/rffe_register_v1/qualification.py)分别承担材料生产、预期语义、真实观察和来源匹配。参考、私有输入与完整日志不进入求解工作区。
