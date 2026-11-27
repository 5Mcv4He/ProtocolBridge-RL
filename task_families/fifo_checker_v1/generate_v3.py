"""Produce previously unqualified depth-one and depth-five checker contracts.

Generation is not admission. Existing depth-two/three packages and evidence are
unchanged; each new depth derives its applicable controls and obligations.
"""
import argparse
import hashlib
import json
from pathlib import Path
from .generate import reference
from .generate_v2 import produce as base_produce, negative_controls as base_controls


def negative_controls(depth):
    if depth not in (1, 5):
        raise ValueError('Revision 3 domain: depths 1 and 5')
    ref = reference(depth)
    cases = base_controls(depth)
    if depth == 1:
        # A one-slot ring has no moving head. Mutating the head update is not a
        # functional defect, and must not be counted as a missed negative.
        del cases['forget_pop_pointer']
        cases['empty_bypass'] = ref.replace('pop && count==0', 'pop && count==0 && !push')
        cases['discard_replacement'] = ref.replace('if(push) begin', 'if(push && !pop) begin')
    else:
        cases['binary_wrap'] = ref.replace('(tail==4)?0:tail+1', '(tail+1)%8').replace('(head==4)?0:head+1', '(head+1)%8')
        cases['rounded_capacity'] = ref.replace('count==5 && !pop', 'count==8 && !pop')
        cases['narrow_count'] = ref.replace('integer count;', 'logic [1:0] count;')
    return cases


def produce(depth, out):
    controls = negative_controls(depth)  # Reject invalid parameters before writes.
    out = Path(out)
    base_produce(depth, out)
    for p in (out/'controls').glob('*.sv'):
        p.unlink()  # Only files created by this invocation in a new directory.
    for name, source in controls.items():
        (out/'controls'/(name+'.sv')).write_text(source)
    task = json.loads((out/'task.json').read_text())
    task.update(verifier='verifier.fifo_checker.campaign_v3', verifier_revision=3,
                generation_revision=3,
                contract_delta=('single-slot old identity versus replacement; no empty bypass'
                    if depth == 1 else 'five slots; capacity needs three bits; modulo-five storage reuse'),
                control_exclusions=({'forget_pop_pointer': 'No pointer movement exists at depth one'} if depth == 1 else {}))
    task['obligations'] += (['single-slot-replacement-preserves-new-identity'] if depth == 1 else ['capacity-five-not-four-or-eight','modulo-five-not-eight'])
    (out/'task.json').write_text(json.dumps(task,indent=2)+'\n')
    (out/'README.md').write_text('''# FIFO 身份检查器：深度 %d

这份候选测量%s。它属于同一个 FIFO 检查能力族，不因参数不同而宣称新增协议能力。

[规格](spec.md)规定事件顺序、容量、复位和错误保持；Agent 只修改 [checker.sv](workspace/checker.sv)。可信 deque 模型和逐周期比较器仍在求解进程之外，无条件通过和无条件拒绝都会被检出。

生成器修订 3 为新深度选择实际有意义的错误对照：单槽没有移动指针，因此不把“冻结 head”算作缺陷；五槽必须验证计数容量和模五回绕，而非仅测试数据能否进出。

## 准入与复现

`python3 -m verifier.fifo_checker.quality_v3 NEW_OUT` 实际运行两种合法结构、公开／终局／保留输入及适用功能反例。生成包本身不授予运行准入；结果、来源和任务文件须完整匹配。原深度 2／3 的契约与门禁保持原版本。

本任务使用 VCS 与独立事件模型，不依赖 VIP，也不将有限测试称为完整形式证明。实际模型校准状态由独立研究记录说明，不能从文件存在推断已校准。
''' % (depth, '单个槽位在退休与替换同拍时是否比较旧身份' if depth==1 else '非二次幂存储在五槽容量与多轮回绕时是否保持请求身份'))
    files = {str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(out.rglob('*')) if p.is_file() and p.name!='generation.json'}
    manifest = {'schema':'fifo-checker-generation-v3','task_id':task['task_id'],
                'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'files':files,'status':'candidate; independent industrial admission required'}
    (out/'generation.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('depth',type=int);p.add_argument('out');a=p.parse_args()
    print(json.dumps(produce(a.depth,a.out),indent=2))
