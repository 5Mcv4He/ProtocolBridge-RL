"""Finite RFFE register contracts with device-specific independent semantics."""
import argparse,hashlib,json
from pathlib import Path
MODES=('rw','w1c')


def rtl(mode,alternate=False):
    if mode not in MODES:raise ValueError('Unsupported register semantics')
    s=Path(__file__).with_name('reference_template.sv').read_text()
    s=s.replace('__RESET__',"8'h00" if mode=='rw' else "8'hff")
    s=s.replace('__UPDATE__','payload[7:0]' if mode=='rw' else 'regs[address]&~payload[7:0]')
    if alternate:
        s=s.replace('command<={command[11:0],ds2};','if(n<12)command[11-n]<=ds2;')
        s=s.replace('payload<={payload[7:0],ds2};','if(n<8)payload[7-n]<=ds2;')
    return s


def controls(mode):
    s=rtl(mode)
    return {
        'no_read_drive':s.replace('sdata_oe<=1;','sdata_oe<=0;'),
        'wrong_read_address':s.replace('regs[command[4:0]]','regs[command[4:0]^1]'),
        'write_alias':s.replace('regs[address]<=','regs[address^1]<='),
        'read_bit_flip':s.replace('sdata_out<=response[8-n];','sdata_out<=~response[8-n];'),
        'parity_inverted':s.replace('~^regs[command[4:0]]','^regs[command[4:0]]'),
        'park_not_zero':s.replace('state<=5;n<=0;sdata_out<=0;','state<=5;n<=0;sdata_out<=1;').replace('5:begin if(rise)begin sdata_out<=0;','5:begin if(rise)begin sdata_out<=1;'),
        'reset_keeps_data':s.replace('for(i=0;i<32;i=i+1)regs[i]<='+ ("8'h00" if mode=='rw' else "8'hff")+';',''),
        'wrong_update_semantics':s.replace('regs[address]<='+('payload[7:0]' if mode=='rw' else 'regs[address]&~payload[7:0]')+';', 'regs[address]<='+('regs[address]&~payload[7:0]' if mode=='rw' else 'payload[7:0]')+';'),
    }


def generate(mode,out):
    if mode not in MODES:raise ValueError('Unsupported register semantics')
    out=Path(out);out.mkdir(parents=True,exist_ok=False);(out/'workspace').mkdir();(out/'controls').mkdir()
    task='rffe_register_'+mode+'_v1'
    semantics=('复位后各寄存器为 0；写入用新字节覆盖选中寄存器。' if mode=='rw' else '复位后各寄存器为 255；写数据的每个 1 清除对应状态位，0 保持原状态，即逐位 W1C（write-one-to-clear）。')
    spec='''# 有限 RFFE 寄存器从设备

该模块接收串行寄存器写入并返回读数据。协议传输相同，但设备内部的更新规则由本任务定义；不能只证明帧合法而忽略地址归属或存储内容。

## 接口与固定数字环境

唯一模块 `rffe_register`，按顺序为输入 `clk,rst_n,sclk,sdata`、输出 `sdata_out,sdata_oe`，均为 1 位。只修改 rffe_register.sv；无参数、外部实例或层次引用。clk 为 500 MHz。rst_n 低有效同步，至少持续 50 个 clk 周期；仅在空闲期复位，复位时清空协议状态并释放输出，下一命令至少延迟 2 us。

外部适配器在 sdata_oe=1 时以推挽方式驱动物理 SDATA 为 sdata_out，否则保持高阻。输入 sclk/sdata 是物理引脚的二态数字采样：高阻空闲在 DUT 接收端解释为 0；VIP 仍观察物理高阻状态，不能用持续驱动 0 冒充释放。无模拟电气或亚稳态模型。

单主设备、单总线、USID=1、SCLK=1 MHz、占空比 50%、RFFE 2.0 普通读模式（VIP sREAD=0，非同步读扩展），只有 Register Write 和 Register Read，每次恰好一个字节。有效地址为 0–15。传输 MSB-first，串行数据在 SCLK 下降沿采样。SSC 为 SCLK 保持低期间的 SDATA 高脉冲；随后发送 4 位 USID、8 位命令和 1 位奇校验。写命令为 0x40+地址，读命令为 0x60+地址。奇校验使对应帧含校验位的异或为 1。

写命令后为 8 位数据、1 位奇校验和主设备 Bus Park。读命令后为主设备 Bus Park，再由候选返回 8 位数据、1 位奇校验，最后由候选执行 Bus Park。普通读数据和校验在相应 SCLK 上升沿后建立、在下降沿前有效；Bus Park 要求在该拍上升沿时 SDATA 已为 0，并在下降沿之后 13 ns 内释放。候选不得在主设备发送期间或空闲期间驱动总线。帧之间至少有 2 us 空闲。

## 寄存器语义

'''+semantics+'''

16 个寄存器独立，读操作无副作用；后续读必须反映此前完成的同地址写入，不能受其他地址访问影响。闲时复位恢复全部寄存器的复位值。数据与地址均为无符号数。写入 0、255、单个位和重复写入均合法。

不要求其他 USID、地址 16–31、广播、Register0 Write、扩展命令、异常奇校验输入、多主设备、总线交接、同步读扩展 sREAD、半速读、其他速率或事务中复位。主设备产生合法请求；候选必须产生合法响应。这是有限数字接口角色，不是完整 RFFE 认证或电气符合性证明。

## 交付与可信验收

提交自包含可综合 RTL。禁止 include、宏、initial、延迟、系统任务、文件操作、测试台和外部代码。Agent 只能读取规格及自身交付，不能访问参考、私有输入或评分器。

VIP 驱动和观察真实事务，独立物理引脚解码核对命令、数据、校验和 Bus Park，任务专用寄存器模型核对读回。VIP 通用存储预测不负责本设备的自定义更新及外部复位语义；这部分由独立判据承担。完整活动和检查通过 reward=1；已确认的功能、时序或编译错误为0；无效提交、环境故障、超时或不完整运行为null。终局和保留评估在停止求解后独立执行，不返回继续修复。没有 PPA 奖励。
'''
    (out/'spec.md').write_text(spec)
    header=rtl(mode).split(' logic cs1')[0]
    (out/'workspace/rffe_register.sv').write_text(header+' always_comb begin sdata_out=0;sdata_oe=0;end\nendmodule\n')
    (out/'reference.sv').write_text(rtl(mode));(out/'alternate.sv').write_text(rtl(mode,True))
    for name,source in controls(mode).items():(out/'controls'/(name+'.sv')).write_text(source)
    metadata=dict(task_id=task,version=1,family='rffe-register-v1',mode=mode,deliverable='rffe_register.sv',verifier='verifier.rffe_register.campaign',verifier_revision=2,
        capabilities=['serial-command-decode','bidirectional-turnaround','register-address-identity', 'overwrite-update' if mode=='rw' else 'write-one-clear-update'],
        obligations=['active-VIP-master-passive-slave','actual-pin-frames','readback-register-model','all-supported-addresses','independent-address-updates','individual-bit-writes','zero-and-repeat-writes','idle-reset-restores-all-registers','odd-parity','read-bus-park-zero-and-release'],
        source_origin='generated empty implementation; controls are synthetic',admission='candidate; industrial controls and matching source required')
    (out/'task.json').write_text(json.dumps(metadata,indent=2)+'\n')
    (out/'README.md').write_text('# RFFE 有限寄存器任务：'+mode+'\n\n[规格](spec.md)定义串行传输与设备状态的关系。只修改 [rffe_register.sv](workspace/rffe_register.sv)。参考与错误对照供可信侧验收，不进入 Agent 工作区。\n\n两种契约共享协议环境；RW 覆盖赋值，W1C 覆盖逐位清除及保持。生成成功不等于准入，模型校准与来源绑定由独立证据记录。有限正反对照不能证明完整协议或验证器完备。\n')
    files={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob('*')) if p.is_file()}
    manifest=dict(schema='rffe-register-generation-v2',task_id=task,generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),template_sha256=hashlib.sha256(Path(__file__).with_name('reference_template.sv').read_bytes()).hexdigest(),files=files,status='candidate; no automatic admission')
    (out/'generation.json').write_text(json.dumps(manifest,indent=2)+'\n');return manifest


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=MODES);p.add_argument('out');a=p.parse_args();print(json.dumps(generate(a.mode,a.out),indent=2))
