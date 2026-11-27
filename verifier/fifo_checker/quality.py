"""Admit checker tasks only after false-positive and false-negative controls."""
import argparse
import json
from pathlib import Path
from .campaign import grade, ROOT, sha
from .model import annotate
from task_families.fifo_checker_v1.generate import reference


def run(out):
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    checks = []

    def record(task, name, source, expected, phase='public', category=None):
        p = out / (task + '-' + name + '.sv')
        p.write_text(source)
        result = grade(task, p, out / (task + '-' + name + '-' + phase), phase)
        ok = result['reward'] == expected and (category is None or result['category'] == category)
        checks.append(dict(task_id=task, control=name, expected_reward=expected,
                           phase=phase, accepted=ok, result=result))
        (out / 'progress.json').write_text(json.dumps(checks, indent=2) + '\n')
        print(task, name, phase, result['category'], ok, flush=True)
        if result['category'].startswith('infrastructure'):
            raise RuntimeError('Stop on infrastructure failure; keep this incomplete gate')

    for depth in (2, 3):
        task = 'fifo_checker_d%d_v1' % depth
        ref, alt = reference(depth), reference(depth, True)
        for name, src in [('ring', ref), ('shift', alt)]:
            for phase in ('public', 'terminal', 'evaluation'):
                record(task, name, src, 1., phase)
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
        for name, src in cases.items():
            record(task, name, src, 0., category='transition_mismatch')
    task = 'fifo_checker_d2_v1'
    record(task, 'empty', '', None, category='invalid_submission')
    record(task, 'renamed_port', reference(2).replace('push_id', 'renamed'), None, category='invalid_submission')
    record(task, 'wrong_width', reference(2).replace('[7:0]', '[8:0]'), None, category='invalid_submission')
    record(task, 'report_spoof', reference(2).replace('endmodule', 'initial $display("PB_CHECKER_COMPLETE"); endmodule'), None, category='invalid_submission')
    record(task, 'syntax_error', reference(2).replace('error<=0;', 'error<=;'), 0., category='compile_error')
    paths = [ROOT / p for p in ('verifier/fifo_checker/model.py', 'verifier/fifo_checker/campaign.py',
             'verifier/fifo_checker/quality.py', 'task_families/fifo_checker_v1/generate.py',
             'verifier/uart_tx/campaign_v4.py', 'verifier/independent_formal/campaign.py',
             'environment/remote_backend.py')]
    result = dict(schema='fifo-checker-quality-v1', accepted=len(checks) == 36 and all(x['accepted'] for x in checks),
                  checks=checks, source_files={str(p.relative_to(ROOT)): sha(p) for p in paths},
                  scope='depth 2 and 3; VCS checks candidate error on every event against independent deque oracle; no VIP protocol claim')
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('out')
    a = p.parse_args()
    r = run(a.out)
    print('accepted', r['accepted'])
    raise SystemExit(0 if r['accepted'] else 1)
