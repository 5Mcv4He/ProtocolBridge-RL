"""Cost/coverage-based production distribution, never held-out-outcome selection.

The frozen input is a narrow aggregate of completed industrial controls and a
confirmed verifier issue. This does not estimate model difficulty or success.
"""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from .batch import DEPENDENCIES, BASE_COMMIT, ROOT, sha, save
from task_families.router_v4.contract import validate


def features(contract):
    windows = contract['windows']; sizes = [n for b, n in windows]
    tags = {'nonpage_base', 'page_crossing', 'response_ownership'}
    if any(n & (n - 1) for n in sizes): tags.add('nonpower_size')
    if min(sizes) == 4: tags.add('single_word_target')
    if any(b >= 2**31 for b, n in windows): tags.add('high_address_target')
    if any(b + n == 2**32 - 8 for b, n in windows): tags.add('near_address_limit')
    if [b for b, n in windows] != sorted(b for b, n in windows): tags.add('unsorted_target_order')
    if any(b + n == c for b, n in windows for c, _ in windows): tags.add('adjacent_targets')
    if any(b + n + 4 == c and not any(d <= b+n < d+m for d,m in windows)
           for b,n in windows for c,_ in windows): tags.add('one_word_gap')
    tags.add('largest_target_' + str(sizes.index(max(sizes))))
    return sorted(tags)


def proposals(include_rejections=False):
    result, rejected = [], []
    sizes = [(4100, 16, 64), (8204, 4, 128), (12292, 28, 256), (16380, 64, 12)]
    for layout in range(6):
        for index, original in enumerate(sizes):
            ns = list(original); offset = (4, 12, 28, 60)[index]
            if layout == 0:
                a = 0x1000 + offset; bases = [a, a + ns[0], a + ns[0] + ns[1]]
            elif layout == 1: bases = [0x10000 + offset, 0x50000 + offset, 0x80010000 + offset]
            elif layout == 2: bases = [0x30000 + offset, 0x1000 + offset, 0x90000000 + offset]
            elif layout == 3: bases = [0x100000 + offset, 2**32 - 8 - ns[1], 0x70000000 + offset]
            elif layout == 4:
                a = 0x20000 + offset; bases = [a, a + ns[0] + 4, 0x1000 + offset]
            else:
                ns = [ns[1], ns[0], ns[2]]; bases = [0x1000 + offset, 0x20000 + offset, 0x40000000 + offset]
            c = dict(task_id='x2p_router_roundword' + chr(ord('a') + layout*4 + index) + '_v1',
                     windows=[[a, n] for a, n in zip(bases, ns)],
                     purpose='Word-aligned routing layout %d: exact base subtraction across a page, small-target bounds, and independently owned B/R responses.' % layout)
            try:
                validate(c)
            except ValueError as error:
                rejected.append(dict(contract=c, reason=str(error),
                                     classification='outside_current_generator_domain',
                                     physically_impossible=False))
                continue
            result.append(c)
    return (result, rejected) if include_rejections else result


def select(evidence, seconds=3600, max_instances=4):
    if set(evidence) != {'schema', 'controls', 'issue', 'issue_evidence_sha256', 'response_owner_challenge_seconds'}:
        raise ValueError('Only industrial aggregate inputs are allowed')
    if evidence['schema'] != 'router-production-feedback-v1' or evidence['issue'] != 'response_owner_unclassified':
        raise ValueError('Unsupported production feedback')
    def duration(x):
        return type(x) in (int, float) and math.isfinite(x) and x > 0
    def digest(x):
        return isinstance(x, str) and re.fullmatch('[0-9a-f]{64}', x) is not None
    if (not evidence['controls'] or not duration(evidence['response_owner_challenge_seconds'])
            or not digest(evidence['issue_evidence_sha256'])
            or any(set(r) != {'task_id', 'wall_seconds', 'evidence_sha256'}
                   or not duration(r['wall_seconds']) or not digest(r['evidence_sha256']) for r in evidence['controls'])):
        raise ValueError('Measured complete-control costs required')
    if len({r['task_id'] for r in evidence['controls']}) != len(evidence['controls']):
        raise ValueError('Repeated cost record')
    if type(seconds) is not int or not 0 < seconds <= 7200 or type(max_instances) is not int or not 1 <= max_instances <= 6:
        raise ValueError('Finite qualification budget required')
    costs = [r['wall_seconds'] for r in evidence['controls']] + [evidence['response_owner_challenge_seconds']]
    estimate = math.ceil(max(costs) * 1.1)
    count = min(max_instances, seconds // estimate)
    candidates, rejected = proposals(True); remaining = list(candidates); chosen = []; covered = set()
    while remaining and len(chosen) < count:
        best = min(remaining, key=lambda c: (-len(set(features(c)) - covered), c['task_id']))
        chosen.append(best['task_id']); covered.update(features(best)); remaining.remove(best)
    return dict(schema='word-owner-selection-v2', producer_sha256=sha(__file__),
                evidence_sha256=hashlib.sha256(json.dumps(evidence, sort_keys=True).encode()).hexdigest(),
                proposed=len(candidates)+len(rejected), static_rejected=rejected,
                candidates=candidates, industrial_selected=chosen,
                covered_contract_tags=sorted(covered), candidate_tags={c['task_id']: features(c) for c in candidates},
                estimated_per_instance_seconds=estimate, qualification_budget_seconds=seconds,
                selection='Greedy new contract-tag coverage; deterministic task-ID tie break; bounded by maximum observed cost plus 10%.',
                mandatory_verifier='response-ownership-v1',
                limits='Predicted cost is not an actual runtime bound. The execution controller must enforce a separate batch wall/resource limit. No held-out or model-success outcomes are read. Parameter contracts are not independent engineering abilities.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('evidence'); p.add_argument('out')
    a = p.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=False)
    result = select(json.loads(Path(a.evidence).read_text())); save(out / 'selection.json', result)
    save(out / 'plan.json', dict(schema='word-owner-production-v1', base_commit=BASE_COMMIT,
                                producer_files={f: sha(ROOT / f) for f in DEPENDENCIES},
                                contracts=result['candidates'],
                                limits={'max_candidates': 24, 'minimum_free_bytes': 2 * 1024**3}))
    print(json.dumps({'candidates': len(result['candidates']), 'selected_for_industrial': result['industrial_selected'],
                      'estimated_per_instance_seconds': result['estimated_per_instance_seconds']}))
