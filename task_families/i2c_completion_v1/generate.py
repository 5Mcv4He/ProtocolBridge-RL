"""Reuse a qualified serial front end while withholding the assessed delivery state."""
import argparse,hashlib,json
from pathlib import Path
from task_families.i2c_sink_v1 import generate_v2 as base
MODES=base.MODES

def scaffold():
    source=Path(base.__file__).with_name('reference_template.sv').read_text()
    source=source.replace('  logic half;logic [7:0] first;\n','')
    source=source.replace('half<=0;first<=0;','/* Initialize your delivery state here. */ ')
    source=source.replace('half<=0;state<=ADDRESS','/* START boundary. */ state<=ADDRESS')
    source=source.replace('half<=0;state<=IDLE','/* STOP boundary. */ state<=IDLE')
    source=source.replace('/* EMIT */','/* BYTE_ACCEPTED: completed byte is {shift[6:0],sda_q}. Add delivery logic. */ ')
    return source

def generate(mode,out):
    base.generate(mode,out);out=Path(out);task='i2c_completion_'+mode+'_v1'
    p=out/'spec.md';s=p.read_text().replace('# I²C 有限写入接收器','# I²C 接收骨架中的数据交付补全')
    s=s.replace('起始文件为空功能模板。','起始文件提供经过独立验收的串行接收、地址识别和 ACK 时序骨架，数据交付尚未实现。标注 BYTE_ACCEPTED 的分支仅在一个完整数据字节接收时执行，完成字节为 {shift[6:0],sda_q}；START、STOP、复位分支也有标记。骨架没有被考察的数据交付或组字状态答案。允许修改整个交付文件，但仍须保持全部原有总线行为。')
    s=s.replace('任务测量串行位接收、ACK 时序及事务边界，word 版本还测量局部组字状态的生命周期。','本版本提供串行协议基础，重点测量数据事件交付；word 版本进一步测量局部组字状态的生命周期。可信侧仍验证完整接口，改动骨架导致的时序回归也会失败。')
    p.write_text(s);(out/'workspace/i2c_sink.sv').write_text(scaffold())
    p=out/'task.json';m=json.loads(p.read_text());m.update(task_id=task,family='i2c-completion-v1',form='scaffold_completion',source_origin='qualified protocol front end with delivery state removed',backend_contract_id='i2c_sink_'+mode+'_v1',assessed_capabilities=['single-cycle-byte-delivery'] if mode=='byte' else ['transaction-local-word-assembly','odd-frame-discard','word-byte-order']);p.write_text(json.dumps(m,indent=2)+'\n')
    (out/'README.md').write_text('# I²C 局部功能补全\n\n[规格](spec.md)沿用有限写入接收器的功能契约，[初始文件](workspace/i2c_sink.sv)提供接收与 ACK 骨架，留出交付逻辑。byte 需要生成单拍字节事件；word 还需正确维护和丢弃半字。\n\n这是同一工程对象的不同任务形式，不新增协议能力。完整验证不因提供骨架而减少；准入证据和模型校准独立记录。\n')
    files={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob('*')) if p.is_file() and p.name!='generation.json'}
    (out/'generation.json').write_text(json.dumps(dict(schema='i2c-completion-generation-v1',task_id=task,generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),base_generator_sha256=hashlib.sha256(Path(base.__file__).read_bytes()).hexdigest(),files=files),indent=2)+'\n');return m

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=MODES);p.add_argument('out');a=p.parse_args();generate(a.mode,a.out)
