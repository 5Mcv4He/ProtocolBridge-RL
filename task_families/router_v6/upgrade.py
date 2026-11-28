"""Compose the same ownership observer with either supported routing domain.

This is execution-component reuse, not inheritance of an instance verdict.
Every new aperture contract still needs full source-bound industrial controls.

The response ownership ledger strengthens checks for an existing requirement;
it does not change the supported task contract. All controls must run again.
"""
import argparse
import json
import shutil
from pathlib import Path
from task_families.router_v2.generate import sha, verify
from task_families.router_v3.materialize import replace_once


def upgrade(parent, out):
    parent, out = Path(parent).resolve(), Path(out).resolve()
    manifest = verify(parent)
    if (manifest.get('family') not in ('x2p_three_target_router_v3', 'x2p_word_aperture_router_execution_v1')
            or manifest.get('qualification_revision') != 2):
        raise ValueError('Expected a supported page/word routing execution capsule')
    if out.exists():
        raise ValueError('Never overwrite a capsule')
    out.mkdir(parents=True)
    for name in manifest['files']:
        dest = out / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(parent / name), str(dest))
    snippet = Path(__file__).resolve().parents[1] / 'router_v5/response_ownership.sv.in'
    tb = out / 'verifier/task002/tb.sv'
    tb.write_text(replace_once(tb.read_text(), ' int cycle=0,aw_cycle=-1,w_cycle=-1;',
                              snippet.read_text() + '\n int cycle=0,aw_cycle=-1,w_cycle=-1;'))
    ref = (out / 'fixtures/task002/reference.sv').read_text()
    # These are synthesizable functional mutations, not compilation failures.
    mutations = (
        ('bad_wrong_read_response.sv', 's_bvalid<=1;', 's_bvalid<=1; s_rvalid<=1;', 'address_data',
         'Write completion also asserts a read response with no accepted AR.'),
        ('bad_wrong_write_response.sv', 's_rvalid<=1;', 's_rvalid<=1; s_bvalid<=1;', 'read_only',
         'Read completion also asserts a write response with no accepted AW/W.'),
    )
    meta_path = out / 'tasks' / manifest['task_id'] / 'task.json'
    meta = json.loads(meta_path.read_text())
    for filename, old, new, case, violation in mutations:
        if ref.count(old) != 2:
            raise ValueError('Reference structure differs; mutation requires review')
        name = 'fixtures/task002/' + filename
        (out / name).write_text(ref.replace(old, new))
        meta['quality']['negative_controls'].append(
            dict(source=name, first_case=case, violation=violation))
    meta['quality']['minimum_negative_controls'] = len(meta['quality']['negative_controls'])
    meta_path.write_text(json.dumps(meta, indent=2) + '\n')
    obligation = dict(id='G_RESPONSE_OWNER', requirement='B requires accepted AW and W; R requires accepted AR; reset cancels ownership.',
                      independent_observer='Interface handshake counts, separate from APB completion credit and VIP transaction tables.',
                      stimuli=['address_data', 'read_only', 'response_backpressure', 'router_reset'],
                      controls=[m[0] for m in mutations],
                      qualification='Both legal structures and every inherited/new negative must be actually executed; no evidence inheritance.')
    (out / 'response-ownership-obligation.json').write_text(json.dumps(obligation, indent=2) + '\n')
    # Update human-facing control counts without touching the functional Spec.
    intro = out / 'tasks' / manifest['task_id'] / 'README.md'
    import re
    text = intro.read_text()
    text = re.sub(r'(?<=Two legal references, )\d+(?= requirement-violating controls)',
                  str(len(meta['quality']['negative_controls'])), text)
    intro.write_text(text)
    files = {name: sha(out / name) for name in manifest['files']}
    for name in ['response-ownership-obligation.json'] + ['fixtures/task002/' + m[0] for m in mutations]:
        files[name] = sha(out / name)
    result = dict(manifest, files=files, family='x2p_three_target_router_v5',
                  verifier_revision='response-ownership-v1', status='candidate_not_admitted',
                  engineering_domain=manifest['family'],
                  verifier_parent_manifest_sha256=sha(parent / 'family-manifest.json'),
                  verifier_upgrade_sha256=sha(__file__), observer_template_sha256=sha(snippet))
    (out / 'family-manifest.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    verify(out)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('parent'); p.add_argument('out')
    a = p.parse_args()
    print(upgrade(a.parent, a.out)['task_id'])
