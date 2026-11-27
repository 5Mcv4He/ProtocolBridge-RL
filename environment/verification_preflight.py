"""Reuse only completed common preflights with identical executable dependencies.

The budget acceptance covers BOTH conditions. This never reuses terminal grades,
model sessions, or compilation products, and does not replace task admission.
"""
import hashlib,json,shutil
from pathlib import Path
NAMES=('runtime-acceptance','synthesis-acceptance','lab-acceptance','mechanism','budget-acceptance')
KEYS=('task_id','source_files','installed_runtime_files','toolchain','task_admission','synthesis_binding','capabilities')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def binding(manifest):return {k:manifest[k] for k in KEYS}
def seal(out,manifest):
    out=Path(out);files={}
    for name in NAMES:
        p=out/name/'result.json'
        if json.loads(p.read_text()).get('accepted') is not True:raise ValueError('Incomplete preflight')
        files[name+'/result.json']=sha(p)
    record={'version':'verification-preflight-v1','binding':binding(manifest),'files':files}
    (out/'preflight-ready.json').write_text(json.dumps(record,indent=2)+'\n')
    return record

def reuse(out,prior,manifest):
    out=Path(out);prior=Path(prior).resolve();proof=prior/'preflight-ready.json'
    record=json.loads(proof.read_text())
    if record['binding']!=binding(manifest) or set(record['files'])!={n+'/result.json' for n in NAMES}:
        raise ValueError('Preflight source/toolchain/admission mismatch')
    for name,digest in record['files'].items():
        p=prior/name
        if sha(p)!=digest or json.loads(p.read_text()).get('accepted') is not True:raise ValueError('Changed preflight evidence')
    for name in NAMES:
        dest=out/name;dest.mkdir()
        shutil.copyfile(str(prior/name/'result.json'),str(dest/'result.json'))
    (out/'preflight-reuse.json').write_text(json.dumps({'version':'verification-preflight-v1','source_record_sha256':sha(proof),'evidence_files':record['files'],'scope':'Same source/toolchain common checks including both public budgets; no model or terminal result reused.'},indent=2)+'\n')
