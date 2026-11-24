import argparse,json
from pathlib import Path
from verifier.grade import grade
def test(work,out): return grade(Path(work)/'bridge.sv',out,public=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('workspace');p.add_argument('out');a=p.parse_args();print(json.dumps(test(a.workspace,a.out)))
