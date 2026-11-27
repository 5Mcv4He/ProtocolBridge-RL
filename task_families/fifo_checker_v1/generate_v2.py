"""Complete candidate packages with explicit interaction obligations.

Generator v1's rejected quality evidence remains separate. This assembler does
not self-admit a package or claim every supported depth has been qualified.
"""
import argparse
import hashlib
import json
from pathlib import Path
from .generate import generate, reference


def negative_controls(depth):
    ref = reference(depth)
    cases = {
        'always_pass': ref.split('  integer count;')[0] + "always_ff @(posedge clk) error<=0;\nendmodule\n",
        'always_reject': ref.split('  integer count;')[0] + "always_ff @(posedge clk) error<=1;\nendmodule\n",
        'no_identity_check': ref.replace('pop_id!=entries[head]', "1'b0"),
        'compare_new_id': ref.replace('pop_id!=entries[head]', 'pop_id!=push_id'),
        'reject_full_exchange': ref.replace('&& !pop', ''),
        'accept_overflow': ref.replace('count==%d && !pop' % depth, 'count>%d && !pop' % depth),
        'clear_error_on_idle': ref.replace('else if(!error)', 'else if(!push && !pop) error<=0;\n    else if(!error)'),
        'reset_keeps_count': ref.replace('count<=0;head<=0;tail<=0;error<=0;', 'head<=0;tail<=0;error<=0;'),
        'forget_pop_pointer': ref.replace('if(pop)head<=', "if(1'b0)head<="),
    }
    if depth == 3:
        cases['binary_wrap'] = ref.replace('(tail==2)?0:tail+1', '(tail+1)%4').replace('(head==2)?0:head+1', '(head+1)%4')
    return cases


def produce(depth, out):
    out = Path(out)
    task = generate(depth, out)
    task['obligations'] += ['identity-after-storage-reuse', 'bad-identity-at-full-exchange',
                            'empty-retirement-after-reuse']
    task['verifier'] = 'verifier.fifo_checker.campaign_v2'
    task['verifier_revision'] = 2
    (out / 'task.json').write_text(json.dumps(task, indent=2) + '\n')
    controls = out / 'controls'
    controls.mkdir()
    for name, src in negative_controls(depth).items():
        (controls / (name + '.sv')).write_text(src)
    (out / 'README.md').write_text('''# FIFO 检查器任务：深度 %d

工程师不仅实现电路，也需要编写能够发现电路错误的验证组件。这份任务让 Agent 实现事务身份检查器：收到入队与退休事件后，判断队列是否保持顺序、容量和复位语义。

**检查器是被测对象，不能决定自己的奖励。** 可信事件模型先计算每周期是否应报错，VCS 再运行候选并逐周期比较。无条件通过漏掉错误；无条件拒绝会误报合法行为，两者都不能获得奖励。

## 阅读与交付

[完整规格](spec.md)规定同周期交换、重复身份、空队列不可直通及错误保持。只修改 [workspace/checker.sv](workspace/checker.sv)。例如旧队首为 7，同时退休 7 和入队 9，应通过且新队首为 9；比较新入队身份会产生误报。

参考、替代结构和 controls 是可信研究材料，不复制进 Agent 工作区。生成成功不表示准入通过：当前生产参数域为 1–5，实际获准深度以独立质量记录为准，不把更多参数值自动计为已验收任务。

## 复现路径

在具有合法 VCS 与项目后端配置的源码环境中，以任务目录中的 Task ID 调用受控 reset/test/submit。研究者也可直接调用 `python3 -m verifier.fifo_checker.campaign_v2 TASK SOURCE OUT` 检查公开行为；这不是模型访问评分器源码的授权。

`python3 -m verifier.fifo_checker.quality_v2 OUT` 执行深度 2、3 的两种合法结构、误报／漏报错误对照、输入边界与三阶段检查。OUT 必须是新目录。source manifest、输入哈希、真实结果共同决定证据适用性；不能修改旧哈希复用准入。

## 验证限制

本任务使用 VCS 和独立 FIFO 事件模型，不声称完成某个 VIP 协议的验收。仿真是有限输入检查；必要覆盖不是完整性证明。真实研究曾发现“回绕”和“错误身份”分别覆盖仍漏测交互，因此修订 2 强制在存储复用后的退休位置注入身份错误。保留评估独立于训练奖励，不回流求解。
''' % depth)
    files = {str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(out.rglob('*')) if p.is_file() and p.name != 'generation.json'}
    manifest = dict(schema='fifo-checker-generation-v2', task_id=task['task_id'],
                    generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    contract_generator_sha256=hashlib.sha256(Path(__file__).with_name('generate.py').read_bytes()).hexdigest(),
                    files=files, status='candidate; no automatic admission')
    (out / 'generation.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('depth', type=int)
    p.add_argument('out')
    a = p.parse_args()
    print(json.dumps(produce(a.depth, a.out), indent=2))
