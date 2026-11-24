import argparse,hashlib,json,shutil
from pathlib import Path
from verifier.campaign import grade
def submit(work,out,reuse_build=None):
    out=Path(out); out.mkdir(parents=True,exist_ok=False)
    source=Path(work)/'bridge.sv'; target=out/'bridge.sv';shutil.copyfile(source,target);target.chmod(0o444)
    (out/'submission.json').write_text(json.dumps({'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}))
    return grade(target,out/'grade',reuse_build=reuse_build)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('workspace');p.add_argument('out');a=p.parse_args();print(json.dumps(submit(a.workspace,a.out)))
