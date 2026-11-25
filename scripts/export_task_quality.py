"""Publish audited task admission evidence without vectors, deployments or EDA logs."""
import argparse,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.export_policy import compact_result

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+'\n')
def export(source,destination,commit):
    source=Path(source);dest=Path(destination)
    report=json.loads((source/'result.json').read_text());freeze=json.loads((source/'freeze.json').read_text())
    if not report.get('accepted') or report['freeze_sha256']!=sha(source/'freeze.json'):raise ValueError('No valid completed gate')
    dest.mkdir(parents=True,exist_ok=False)
    write(dest/'result.json',report);write(dest/'freeze.json',freeze)
    write(dest/'isolation.json',json.loads((source/'isolation.json').read_text()))
    for name in report['results']:
        p=source/name/'result.json'
        if p.exists():write(dest/name/'result.json',compact_result(json.loads(p.read_text())))
    for p in (source/'mechanism').rglob('result.json'):
        r=json.loads(p.read_text())
        if p.parent==source/'mechanism':write(dest/'mechanism/result.json',r)
        elif 'cases' in r:write(dest/p.relative_to(source),compact_result(r))
    write(dest/'raw-evidence-sha256.json',{str(p.relative_to(source)):sha(p) for p in sorted(source.rglob('*')) if p.is_file()})
    write(dest/'publication.json',{'format':'task-quality-allowlist-v1','source_commit':commit,'task_id':report['task_id'],
      'scope':'Actual control campaigns, mechanism checks and source/toolchain binding. Private raw vectors, deployment files and vendor logs retained on trusted host.',
      'files':{str(p.relative_to(dest)):sha(p) for p in sorted(dest.rglob('*')) if p.is_file()}})
    return verify(dest)
def verify(root):
    root=Path(root);p=json.loads((root/'publication.json').read_text());r=json.loads((root/'result.json').read_text())
    for name,digest in p['files'].items():
        if sha(root/name)!=digest:raise ValueError('Published file hash mismatch: '+name)
    if r['freeze_sha256']!=sha(root/'freeze.json') or not r['accepted']:raise ValueError('Admission mismatch')
    for name,value in r['results'].items():
        c=json.loads((root/name/'result.json').read_text())
        if c.get('reward')!=value['reward'] or c.get('category')!=value['category']:raise ValueError('Control summary mismatch')
    return {'published_consistency':True,'task_id':r['task_id'],'positive_controls':r['positive_count'],'negative_controls':r['negative_count'],'scope':'Published file hashes and summary linkage; not RTL replay or independent proof of Spec completeness.'}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('destination',nargs='?');p.add_argument('--commit');p.add_argument('--verify',action='store_true');a=p.parse_args()
    if a.verify:r=verify(a.source)
    else:
        if not a.destination or not a.commit:p.error('destination and --commit required')
        r=export(a.source,a.destination,a.commit)
    print(json.dumps(r,indent=2))
