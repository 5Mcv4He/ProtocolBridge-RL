"""Admit checker tasks only after false-positive and false-negative controls."""
import argparse
import json
from pathlib import Path
from .campaign_v2 import grade, ROOT, sha
from .model_v2 import annotate
from task_families.fifo_checker_v1.generate import reference
from task_families.fifo_checker_v1.generate_v2 import negative_controls


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
        cases = negative_controls(depth)
        for name, src in cases.items():
            record(task, name, src, 0., category='transition_mismatch')
    task = 'fifo_checker_d2_v1'
    record(task, 'empty', '', None, category='invalid_submission')
    record(task, 'renamed_port', reference(2).replace('push_id', 'renamed'), None, category='invalid_submission')
    record(task, 'wrong_width', reference(2).replace('[7:0]', '[8:0]'), None, category='invalid_submission')
    record(task, 'report_spoof', reference(2).replace('endmodule', 'initial $display("PB_CHECKER_COMPLETE"); endmodule'), None, category='invalid_submission')
    record(task, 'syntax_error', reference(2).replace('error<=0;', 'error<=;'), 0., category='compile_error')
    paths = [ROOT / p for p in ('verifier/fifo_checker/model_v2.py', 'verifier/fifo_checker/campaign_v2.py',
             'verifier/fifo_checker/quality_v2.py', 'task_families/fifo_checker_v1/generate_v2.py', 'task_families/fifo_checker_v1/generate.py',
             'verifier/uart_tx/campaign_v4.py', 'verifier/independent_formal/campaign.py',
             'environment/remote_backend.py')]
    result = dict(schema='fifo-checker-quality-v2', accepted=len(checks) == 36 and all(x['accepted'] for x in checks),
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
