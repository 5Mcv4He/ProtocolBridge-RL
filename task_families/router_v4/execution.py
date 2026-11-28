"""Apply the qualified deployment wrapper to a word-aperture candidate.

This shares execution plumbing only. Its novel address contract still requires
its own industrial controls; neither generation nor this adapter grants admission.
"""
import argparse,json,shutil,subprocess,sys
from pathlib import Path
from task_families.router_v2.generate import verify,sha
from task_families.router_v3.materialize import adapt


def materialize(parent,out):
    parent=Path(parent).resolve();out=Path(out).resolve();m=verify(parent)
    if m.get('family')!='x2p_word_aperture_router_v1':raise ValueError('Expected word-aperture source candidate')
    out.mkdir(parents=True,exist_ok=False)
    for name in m['files']:
        p=out/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(str(parent/name),str(p))
    campaign=out/'verifier/task002/campaign.py';campaign.write_text(adapt(campaign.read_text()))
    driver=Path(__file__).resolve().parents[1]/'router_v3/qualification_v2.py'
    dest=out/'task_families/router_v3/qualification_v2.py';dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(str(driver),str(dest))
    (out/'.local').mkdir()
    tests=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-q'],cwd=str(out),stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    (out/'.local/adapter-tests.log').write_bytes(tests.stdout)
    if tests.returncode:raise ValueError('Execution package checks failed; preserved for review')
    files={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file() and not set(p.relative_to(out).parts)&{'.local','__pycache__'}}
    m=dict(m,files=files,family='x2p_word_aperture_router_execution_v1',execution_adapter='router-deployment-v1',
           qualification_revision=2,parent_manifest_sha256=sha(parent/'family-manifest.json'),
           adapter_sources={str(p.relative_to(Path(__file__).resolve().parents[2])):sha(p) for p in (Path(__file__).resolve(),driver,Path(__file__).resolve().parents[1]/'router_v3/materialize.py')},status='candidate_not_admitted')
    (out/'family-manifest.json').write_text(json.dumps(m,indent=2,sort_keys=True)+'\n');verify(out);return m

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('parent');p.add_argument('out');a=p.parse_args();m=materialize(a.parent,a.out)
    print(json.dumps({'task_id':m['task_id'],'family':m['family'],'status':m['status']}))
