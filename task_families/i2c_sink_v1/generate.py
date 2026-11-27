"""Finite I2C write sinks: byte delivery versus transaction-local word assembly."""
import argparse, hashlib, json
from pathlib import Path
MODES = ('byte', 'word')

def rtl(mode, alternate=False):
    if mode not in MODES:
        raise ValueError('Unsupported delivery mode')
    s = Path(__file__).with_name('reference_template.sv').read_text()
    emit = "item_data<={8'b0,shift[6:0],sda_q};item_valid<=1;"
    if mode == 'word':
        emit = "if(!half)begin first<={shift[6:0],sda_q};half<=1;end else begin item_data<={first,shift[6:0],sda_q};item_valid<=1;half<=0;end"
    s = s.replace('/* EMIT */', emit)
    if alternate:
        s = s.replace('shift<={shift[6:0],sda_q};', 'shift[7-bits]<=sda_q;').replace('shift[6:0],sda_q', 'shift[7:1],sda_q')
    return s

def controls(mode):
    s = rtl(mode)
    result = {
        'reset_data_not_cleared': s.replace('item_data<=0;', ''),
        'wrong_address': s.replace("8'ha4", "8'ha6"),
        'data_bit_loss': s.replace('item_data<=', 'item_data<=16\'h0080 ^ '),
        'ack_too_early': s.replace('drive_delay<=35', 'drive_delay<=1'),
        'no_ack': s.replace('sda_drive_low<=drive_target', 'sda_drive_low<=0'),
        'valid_stuck': s.replace('sda_prev<=sda_q;item_valid<=0;', 'sda_prev<=sda_q;'),
    }
    if mode == 'word':
        result['partial_word_crosses_stop'] = s.replace('half<=0;state<=ADDRESS', 'state<=ADDRESS').replace('half<=0;state<=IDLE', 'state<=IDLE')
        result['byte_order'] = s.replace('{first,shift[6:0],sda_q}', '{shift[6:0],sda_q,first}')
    return result

def generate(mode, out):
    if mode not in MODES:
        raise ValueError('Unsupported mode')
    out = Path(out); out.mkdir(parents=True, exist_ok=False)
    (out/'workspace').mkdir(); (out/'controls').mkdir()
    behavior = ('每个数据字节独立交付，item_data[15:8] 必须为 0。' if mode == 'byte' else
        '每笔写事务内按接收顺序把两个字节组成一个 16 位字，第一个字节在高 8 位。奇数长度事务的最后一个字节不产生输出，STOP 必须丢弃该半字，不能与下一笔事务拼接。')
    spec = '''# I²C 有限写入接收器

主设备通过串行总线写入数据，本模块将它转换为系统时钟域中的单拍数据事件。任务测量串行位接收、ACK 时序及事务边界，word 版本还测量局部组字状态的生命周期。

## 固定接口与时钟

唯一模块 `i2c_sink`，端口按顺序为输入 `clk,rst_n,scl,sda`（各 1 位），输出 `sda_drive_low,item_valid`（各 1 位）及 `item_data[15:0]`。只修改 i2c_sink.sv；无参数、其他模块、外部实例或层次引用。clk 为 100 MHz。rst_n 为低有效同步复位，持续至少 3 个 clk 上升沿；复位后两个控制输出和 item_data 均为 0。只在总线空闲时复位，开始下一事务前至少等待 10 个 clk 周期。

`sda_drive_low=1` 请求外部开漏驱动将 SDA 拉低，0 表示释放；不得驱动高电平。DUT 不驱动 SCL。内部可同步采样输入，不能假定 SCL 边沿对齐 clk。信号只有 0/1，无毛刺或模拟亚稳态模型。

## 支持的总线与交付行为

支持单主设备、7 位地址 0x52、写方向、MSB-first、100 kHz Standard-mode 的合法写事务。每笔包含 START、地址字节 0xA4、1–17 个数据字节、STOP；每个字节后有第 9 拍 ACK。主设备满足 Standard-mode 建立／保持、START、STOP 及总线空闲时间。必须对地址和每个数据字节 ACK。ACK 在第 8 拍之后的 SCL 低期间建立，在第 9 拍之后的低期间释放；与 ACK 有关的 SDA 输出变化距对应 SCL 下降沿为 300–1000 ns，并在 SCL 高期间稳定。该范围是本任务固定的数字时序契约。

''' + behavior + '''

每个应交付的 item_valid 为恰好一个 clk 周期，与 item_data 同步更新；数据在 item_valid=1 时有效。交付必须在该项最后数据位的 SCL 上升沿之后 8 个 clk 周期内发生，不能提前、丢失、重复或重排。没有输出反压。item_valid=0 时 item_data 可以保持或改变。

不测试其他地址、读方向、10 位地址、重复 START、仲裁、多主设备、时钟拉伸、畸形帧、总线恢复、事务中复位或不符合上述时序的输入。这是有限写入角色，不是完整 I²C 控制器。

## 交付与验收边界

起始文件为空功能模板。提交自包含可综合 SystemVerilog；不允许 initial、延迟、宏、include、系统任务、文件操作、可执行测试台或外部资源。公开运行只返回受控结果，不能读取可信参考、验证器或私有输入。

可信侧由工业 VIP 主设备产生事务并检查总线协议，另以引脚事件解码核对实际字节、ACK、数据交付时刻、次数和 STOP 局部状态。VIP 无错误不单独构成功能通过。候选源代码与提交哈希绑定。完整检查通过 reward=1；确认的编译、协议时序或交付功能错误为0；无效提交、基础设施故障和不完整验证为null。保留评估独立执行，不回流求解。没有 PPA 奖励。
'''
    (out/'spec.md').write_text(spec)
    task = f'i2c_sink_{mode}_v1'
    meta = dict(task_id=task, version=1, family='i2c-sink-v1', mode=mode, deliverable='i2c_sink.sv',
        capabilities=['serial-write-reception','open-drain-ack-timing']+(['transaction-local-word-assembly'] if mode=='word' else []),
        obligations=['bit-order','address-ack','every-data-ack','ack-hold','single-cycle-delivery','delivery-latency','frame-order','reset-idle']+(['odd-frame-discard','word-byte-order'] if mode=='word' else []),
        admission='candidate; real independent positive/negative gate required')
    (out/'task.json').write_text(json.dumps(meta, indent=2)+'\n')
    (out/'reference.sv').write_text(rtl(mode)); (out/'alternate.sv').write_text(rtl(mode, True))
    (out/'workspace/i2c_sink.sv').write_text('module i2c_sink(input logic clk,rst_n,scl,sda,output logic sda_drive_low,item_valid,output logic [15:0] item_data);\n always_ff @(posedge clk)begin sda_drive_low<=0;item_valid<=0;item_data<=0;end\nendmodule\n')
    for name, source in controls(mode).items():
        (out/'controls'/f'{name}.sv').write_text(source)
    (out/'README.md').write_text('# 有限 I²C 写入任务\n\n从[规格](spec.md)和[初始 RTL](workspace/i2c_sink.sv)开始。byte 交付每个字节；word 交付事务内的双字节组，并丢弃 STOP 前的残余半字。这一差异引入了状态生命周期要求，并非仅更换随机输入。\n\n参考与错误对照只供可信验收使用。生成包本身不代表准入、完整协议支持或已经运行模型；实际状态由来源匹配的质量证据决定。\n')
    files={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file()}
    (out/'generation.json').write_text(json.dumps(dict(schema='i2c-sink-generation-v1',generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),template_sha256=hashlib.sha256(Path(__file__).with_name('reference_template.sv').read_bytes()).hexdigest(),files=files),indent=2)+'\n')
    return meta

if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=MODES);p.add_argument('out');a=p.parse_args();print(json.dumps(generate(a.mode,a.out),indent=2))
