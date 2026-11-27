"""Bounded status-register contracts; priority is functional, not a seed change."""
import argparse,json,hashlib
from pathlib import Path

MODES=('set_dominant','clear_dominant')

def rtl(mode,alternate=False):
    if mode not in MODES:raise ValueError('Unsupported priority')
    head='module status_register(input logic clk,rst_n,sw_write,input logic [7:0] hw_set,sw_data,output logic [7:0] status);\n'
    if not alternate:
        expr='(status & ~(sw_write ? sw_data : 8\'b0)) | hw_set' if mode=='set_dominant' else '(status | hw_set) & ~(sw_write ? sw_data : 8\'b0)'
        body='always_ff @(posedge clk) begin\n if(!rst_n) status<=0;\n else status<='+expr+';\nend\n'
    else:
        branches=('if(hw_set[i]) status[i]<=1; else if(sw_write && sw_data[i]) status[i]<=0;' if mode=='set_dominant' else 'if(sw_write && sw_data[i]) status[i]<=0; else if(hw_set[i]) status[i]<=1;')
        body='always_ff @(posedge clk) begin\n if(!rst_n) status<=0;\n else for(integer i=0;i<8;i=i+1) begin '+branches+' end\nend\n'
    return head+body+'endmodule\n'

def controls(mode):
    s=rtl(mode)
    return {'wrong_priority':rtl('clear_dominant' if mode=='set_dominant' else 'set_dominant'),
        'clear_without_write':s.replace('sw_write ? sw_data : 8\'b0','sw_data'),
        'clear_all_bits':s.replace('sw_write ? sw_data : 8\'b0','sw_write ? 8\'hff : 8\'b0'),
        'lost_hardware_bits':s.replace('| hw_set','| (hw_set & 8\'h0f)'),
        'reset_ignored':s.replace('if(!rst_n) status<=0;','if(1\'b0) status<=0;'),
        'async_reset':s.replace('posedge clk','posedge clk or negedge rst_n')}

def generate(mode,out):
    if mode not in MODES:raise ValueError('Unsupported mode')
    out=Path(out);out.mkdir(parents=True,exist_ok=False);(out/'workspace').mkdir();(out/'controls').mkdir()
    t='status_'+mode+'_repair_v1';winner='硬件置位' if mode=='set_dominant' else '软件清除'
    spec='''# 修复 8 位硬件状态寄存器

硬件事件将状态位置为 1，软件通过写 1 清除（W1C）已处理的事件。两者可能在同一周期作用于同一位，必须按本契约处理，不能丢失或延后应发生的更新。

唯一模块 status_register。输入 clk、rst_n、sw_write 为 1 位，hw_set、sw_data 为 8 位无符号，输出 status 为 8 位。端口按上述顺序；可用 ANSI 声明。没有其他端口或参数。只修改 status_register.sv。

在 clk 上升沿，低有效同步复位 rst_n=0 优先，将 status 全部清零。其他周期，每位独立：hw_set[i]=1 请求置位，sw_write=1 且 sw_data[i]=1 请求清零；没有请求则保留。sw_write=0 时忽略全部 sw_data。写 0 不清除任何位。置位和清除作用于不同位时同时生效；作用于同一位时，%s优先。不允许将某个位的请求影响其他位。复位信号在时钟沿之间改变时，status 不应异步改变。没有延迟响应、读副作用或队列。

例如旧值 0x81、hw_set=0x42、sw_write=1、sw_data=0xC0，同沿之后应为 %s。复位与所有请求同时出现时应为 0x00。持续的 hw_set 在每个时钟沿都有效，不是只检测上升沿。

起始实现为人工构造的优先级错误，可能需要检查其他关系。交付自包含可综合 RTL，保留接口；禁止 initial、延迟、宏、include、系统任务、外部实例、层次引用、属性假设及可执行测试台。

可信侧将候选与独立参考进行 Formality 顺序等价比较，并以独立的逐位真值表仿真核对同步复位及必要状态更新。候选不能修改参考、脚本、输入或检查器。公开工具只给经过筛选的类别、源码身份和测试余额；终局及保留结果不会回流求解。

有效实现不等价、实际状态错误或编译错误得到 Reward=0；完整必要检查通过得到1；无效交付、工具故障、超时、黑盒、缺失比较点或未完成检查得到null。功能奖励不包含面积、时序或功耗。有限仿真和指定等价范围不构成任意系统环境的正确性证明。
'''%(winner,'0x43' if mode=='set_dominant' else '0x03')
    (out/'spec.md').write_text(spec)
    meta=dict(task_id=t,version=1,family='status-register-v1',mode=mode,deliverable='status_register.sv',capabilities=['write-one-to-clear','per-bit-hardware-software-priority','synchronous-state-update'],obligations=['same-bit-conflict','cross-bit-independence','write-enable-mask','hold-and-repeated-set','reset-priority','no-asynchronous-reset'],initial_origin='controlled wrong-priority mutation',admission='candidate; independent controls and source-matched gate required')
    (out/'task.json').write_text(json.dumps(meta,indent=2)+'\n');(out/'reference.sv').write_text(rtl(mode));(out/'alternate.sv').write_text(rtl(mode,True));(out/'workspace/status_register.sv').write_text(controls(mode)['wrong_priority'])
    for name,s in controls(mode).items():(out/'controls'/(name+'.sv')).write_text(s)
    (out/'README.md').write_text('''# 状态寄存器修复任务

软件清除状态与硬件报告事件可能发生在同一拍。该任务测量模型能否正确处理逐位优先级、写入掩码和同步复位，而不是仅通过一次综合。

从[规格](spec.md)与[起始文件](workspace/status_register.sv)开始。参考及错误对照属于可信研究材料，不复制给求解 Agent。两种优先级是明确不同的工程契约；不按随机种子统计新任务。

生成包是候选。只有同版本参考与替代结构通过、针对性错误被拒绝、独立真值表锚点实际执行后才可准入。没有 PPA 奖励，也不要求候选与其自身综合网表的一致性代替独立参考。
''')
    files={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file()}
    (out/'generation.json').write_text(json.dumps(dict(schema='status-register-generation-v1',generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),files=files),indent=2)+'\n')
    return meta

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=MODES);p.add_argument('out');a=p.parse_args();print(json.dumps(generate(a.mode,a.out),indent=2))
