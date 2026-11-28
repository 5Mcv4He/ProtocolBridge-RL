"""Reconcile legacy hashes of shell output without rewriting historic evidence.

The old deployment wrapper hashed connection diagnostics together with the
sha256sum line. A reconciliation must reproduce both exact old outputs, and
both must contain exactly one identical digest for the configured file.
"""
import hashlib,json,re
from pathlib import Path

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def match(config,first,second,proof=None):
    if first==second:return {'kind':'identical_command_output','sha256':first}
    if proof is None:raise ValueError('Different environment observations require explicit evidence')
    p=Path(proof);r=json.loads(p.read_text());cfg=json.loads(Path(config).read_text())
    if r.get('schema')!='environment-output-reconciliation-v1' or r.get('config_sha256')!=sha(config) or r.get('environment_entry')!=cfg['eda_env_script']:raise ValueError('Reconciliation configuration mismatch')
    rows=r['observations']
    if len(rows)!=2 or {x['mode'] for x in rows}!={'local','remote'}:raise ValueError('Missing execution-mode observations')
    hashes=set();contents=set()
    for x in rows:
        digest=hashlib.sha256(x['output'].encode()).hexdigest()
        matches=re.findall(r'^([0-9a-f]{64})  '+re.escape(cfg['eda_env_script'])+r'$',x['output'],re.M)
        if digest!=x['output_sha256'] or len(matches)!=1 or matches[0]!=x['content_sha256']:raise ValueError('Unbound reconciliation observation')
        hashes.add(digest);contents.add(matches[0])
    if hashes!={first,second} or len(contents)!=1:raise ValueError('Environment outputs do not establish identical file content')
    return {'kind':'reproduced_outputs_same_file_content','content_sha256':contents.pop(),'proof':str(p.resolve()),'proof_sha256':sha(p)}
