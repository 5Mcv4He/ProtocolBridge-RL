"""Two finite combinational synthesis repairs; no technology-dependent PPA target."""
import argparse,hashlib,json
from pathlib import Path
MODES=('population','trailing_zero')
HEADER='module bitfold(input logic [7:0] data,output logic [3:0] result);\n'

def rtl(mode,alternate=False):
    if mode not in MODES:raise ValueError('Unknown bit operation')
    if mode=='population':
        body=(' always_comb result={3\'b0,data[0]}+{3\'b0,data[1]}+{3\'b0,data[2]}+{3\'b0,data[3]}+{3\'b0,data[4]}+{3\'b0,data[5]}+{3\'b0,data[6]}+{3\'b0,data[7]};\n' if alternate else ' integer i;always_comb begin result=0;for(i=0;i<8;i=i+1)result=result+data[i];end\n')
    else:
        body=(' always_comb begin result=8;for(integer i=7;i>=0;i=i-1)if(data[i])result=i;end\n' if alternate else " always_comb begin casez(data)\n 8'b???????1:result=0;8'b??????10:result=1;8'b?????100:result=2;8'b????1000:result=3;\n 8'b???10000:result=4;8'b??100000:result=5;8'b?1000000:result=6;8'b10000000:result=7;default:result=8;endcase end\n")
    return HEADER+body+'endmodule\n'

def initial(mode):
    if mode=='population':body='while(work!=0)begin work=work&(work-1);result=result+1;end'
    elif mode=='trailing_zero':body='if(work==0)result=8;else while(!work[0])begin work=work>>1;result=result+1;end'
    else:raise ValueError('Unknown bit operation')
    return HEADER+' logic[7:0] work;always_comb begin work=data;result=0;'+body+' end\nendmodule\n'

def controls(mode):
    s=rtl(mode)
    if mode=='population':
        wrong=s.replace('i<8','i<7');corner=s.replace('end\nendmodule','if(data==255)result=7;end\nendmodule')
    else:
        wrong=s.replace("8'b???????1:result=0","8'b???????1:result=1");corner=s.replace('default:result=8','default:result=0')
    return {'wrong_bit':wrong,'wrong_boundary':corner,'constant_zero':HEADER+'always_comb result=0;endmodule\n',
            'data_dependent_loop':initial(mode),
            'latch':HEADER+'always_latch if(data!=0) result=data[3:0];endmodule\n'}

def generate(mode,out):
    if mode not in MODES:raise ValueError('Unknown bit operation')
    out=Path(out);out.mkdir(parents=True,exist_ok=False);(out/'workspace').mkdir();(out/'controls').mkdir()
    task='bitfold_'+mode+'_repair_v1'
    contract=('result 是 data 中 1 的个数（0–8）。例如 0→0，128→1，255→8。' if mode=='population' else 'result 是 data 从最低位开始连续 0 的个数；data=0 时 result=8。例如 1→0，128→7，40→3，0→8。')
    (out/'spec.md').write_text('''# 将有限位运算改写为可综合的组合电路

软件式循环可以在仿真中给出正确答案，却不一定能被综合器展开为有限硬件。本任务要求保留行为，修复起始实现中的数据相关循环，使它能通过固定的 Design Compiler 综合流程。起始缺陷为人工构造，不是历史模型错误。

## 功能与交付

唯一交付 `bitfold.sv`，唯一模块 `bitfold(input logic [7:0] data, output logic [3:0] result)`。接口顺序、方向和位宽固定，无参数、时钟、复位或其他端口。所有 256 种二态输入均受支持；没有未指定的二态输入。\n\n'''+contract+'''

输出只能依赖当前输入，不得保留历史状态。没有时钟周期延迟；无需定义 X/Z 输入的功能。只修改这一个自包含 SystemVerilog 文件。禁止 include、宏、initial、延迟、系统任务、外部实例、层次访问和候选 Tcl。

## 工程条件与独立验收

必须能在指定 Design Compiler O-2018.06-SP1 流程中完成分析、展开、链接、设计检查及映射，综合网表不含锁存器、触发器或其他未映射单元。没有面积、时序或功耗阈值；教学库仅支持流程与结构验收，不代表真实工艺 PPA。

可信侧分别执行：独立整数模型的穷举输入检查；与独立可信 RTL 的 Formality 等价；固定综合；候选 RTL 与自身综合网表的 Formality 等价。后两种等价关系职责不同，不能互相代替。无黑盒、缺失比较点、未证明点或中止点才能接受证明。公开 test 对当前源码运行同一类必要检查，终局与保留评估在提交结束后执行，不能据此继续修复。

完整通过 reward=1；已确认的功能、编译或综合结构错误为0；无效提交、基础设施错误、超时或不完整验证为null。Agent 只能读规格和自身源码，不能修改参考、库、约束、检查器和私有输入。
''')
    (out/'workspace/bitfold.sv').write_text(initial(mode));(out/'reference.sv').write_text(rtl(mode));(out/'alternate.sv').write_text(rtl(mode,True))
    for name,source in controls(mode).items():(out/'controls'/(name+'.sv')).write_text(source)
    metadata=dict(task_id=task,version=1,family='bitfold-synth-v1',mode=mode,deliverable='bitfold.sv',verifier='verifier.bitfold_synth.campaign',verifier_revision=1,source_origin='synthetic data-dependent-loop repair',capabilities=['bounded-hardware-elaboration','combinational-state-exclusion',mode],obligations=['all-256-inputs','zero-and-extreme-inputs','order-independent-output','independent-reference-equivalence','complete-mapped-combinational-netlist','candidate-to-netlist-equivalence'],admission='candidate; matching industrial gate required')
    (out/'task.json').write_text(json.dumps(metadata,indent=2)+'\n')
    (out/'README.md').write_text('# 有限组合位运算修复\n\n[规格](spec.md)解释为什么正确仿真仍可能无法综合。可信侧分别检查功能、硬件结构和变换一致性；不会用候选自身网表充当独立答案。\n\n[起始文件](workspace/bitfold.sv)含人工构造的数据相关循环。生成不等于准入，模型试次另行冻结。\n')
    files={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob('*')) if p.is_file()}
    manifest=dict(schema='bitfold-generation-v1',task_id=task,generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),files=files)
    (out/'generation.json').write_text(json.dumps(manifest,indent=2)+'\n');return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=MODES);p.add_argument('out');a=p.parse_args();generate(a.mode,a.out)
