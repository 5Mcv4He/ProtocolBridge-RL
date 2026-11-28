"""Replay a composed capsule's recorded grading without EDA or private feedback.

Checks source, full input role, serialized vectors, compiler attribution and
per-case parser replay. This audits the observed evidence, not oracle completeness.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from environment.composed_backend_v1 import sha
from task_families.router_v3.toolchain import observed, check


def read(p):
    return json.loads(Path(p).read_text())


def audit(package, directory, config, cases, phase, source_sha256):
    package, directory = Path(package), Path(directory)
    r = read(directory/'result.json')
    if r['source_sha256'] != source_sha256 or r['public'] != (phase == 'public'):
        raise ValueError('Graded source or role differs')
    if r['category'] == 'invalid_submission':
        if r['reward'] is not None or (directory/'runtime.json').exists():
            raise ValueError('Invalid source unexpectedly executed')
        return dict(category=r['category'], reward=None, simulation_records=0)
    if (read(directory/'cases.json') != cases or sha(directory/'cases.json') != r['suite_sha256']
            or sha(directory/'bridge.sv') != source_sha256):
        raise ValueError('Actual source or input differs')
    cfg = read(config)
    rt = read(directory/'runtime.json')
    expected = {p.name: sha(p) for p in (package/'verifier/task003').glob('*.sv')}
    expected.update(candidate=source_sha256, campaign=sha(package/'verifier/task003/campaign.py'),
        build_configuration=hashlib.sha256(json.dumps({k:v for k,v in cfg.items()
            if k not in ('variant','remote_root')},sort_keys=True).encode()).hexdigest())
    if set(rt['inputs']) != set(expected)|{'environment_entry'} or any(rt['inputs'][k]!=v for k,v in expected.items()):
        raise ValueError('Build dependencies differ')
    if r.get('compile_reused'):
        raise ValueError('Standalone submission cannot reuse a control build')
    if r['category'] == 'compile_error':
        log = (directory/'compile.log').read_text()
        errors = re.findall(r'Error-\[.*?(?=\nError-|\Z)',log,re.S)
        if (not r['compile_exit'] or not errors or not all('bridge.sv' in e[:300] for e in errors)
                or re.search(r'LICENS|Cannot find',log) or r['reward'] != 0 or r['cases']):
            raise ValueError('Compiler failure not attributable to candidate')
        return dict(category=r['category'], reward=0, simulation_records=0)
    backend = read(directory/'backend.json')
    if backend['inputs'] != rt['inputs'] or backend['remote'] != rt['remote'] or r['compile_exit'] != 0:
        raise ValueError('Successful build evidence missing')
    if not r['cases'] or [c['name'] for c in r['cases']] != [c['name'] for c in cases[:len(r['cases'])]]:
        raise ValueError('Missing or reordered simulation')
    for c, saved in zip(cases,r['cases']):
        d=directory/c['name']
        vectors='%d %d %d\n'%(c.get('reset_stage',0),len(c['rows']),len(c.get('recovery',[])))
        vectors+=''.join('%d %08x %08x %x %d %d %d %d %d %d\n'%tuple(x) for x in c['rows']+c.get('recovery',[]))
        if (d/'vectors.txt').read_text()!=vectors or read(d/'result.json')!=saved:
            raise ValueError('Per-case record or stimulus differs')
        check(observed((d/'simulation.log').read_text()),cfg['toolchain'])
    # Capsule interpreter is isolated from another instance's imported modules.
    code='''import json,sys
from pathlib import Path
from verifier.task003.campaign import interpret,REQUIRED_BINS
p=Path(sys.argv[1]);r=json.loads((p/'result.json').read_text());cases=json.loads((p/'cases.json').read_text());seen=set()
for c,s in zip(cases,r['cases']):
 x=interpret((p/c['name']/'simulation.log').read_text(),s['simulation_exit'],c)
 if any(s.get(k)!=v for k,v in x.items()):raise ValueError('Parser replay differs')
 seen.update(s.get('coverage_bins',[]))
if r['reward']==1:
 if len(r['cases'])!=len(cases) or not r['verification_complete'] or any(x['reward']!=1 for x in r['cases']):raise ValueError('Incomplete success')
 for k in ('planned','checked','aborted'):
  if r[k]!=sum(x['scoreboard'][k] for x in r['cases']):raise ValueError('Transaction accounting differs')
 if not r['public'] and (not REQUIRED_BINS<=seen or r['functional_cross']!={'required':len(REQUIRED_BINS),'observed':len(seen&REQUIRED_BINS),'missing':[],'kind':'requirement_bins_not_cartesian_cross'}):raise ValueError('Missing interaction coverage')
else:
 last=r['cases'][-1]
 if r['reward']!=last['reward'] or r['category']!=last['category'] or r.get('failed_case')!=last['name'] or any(x['reward']!=1 for x in r['cases'][:-1]):raise ValueError('Failure attribution differs')
print(len(r['cases']))
'''
    env={k:os.environ[k] for k in ('PATH','HOME','LANG') if k in os.environ}
    p=subprocess.run([sys.executable,'-c',code,str(directory.resolve())],cwd=str(package),env=env,
                     stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=60)
    if p.returncode or int(p.stdout)!=len(r['cases']):
        raise ValueError('Frozen verdict replay failed')
    return dict(category=r['category'],reward=r['reward'],simulation_records=len(r['cases']),
                environment_entry_sha256=rt['inputs']['environment_entry'])
