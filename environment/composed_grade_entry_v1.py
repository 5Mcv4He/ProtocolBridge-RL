"""Trusted subprocess entry for explicit frozen inputs and evaluation role.

Launched from a verified composed capsule. This is not an Agent tool or a general
module runner. Role controls the existing campaign's coverage rules unchanged.
"""
import argparse,json,sys
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('out');p.add_argument('inputs');p.add_argument('phase',choices=('public','terminal','heldout'));a=p.parse_args()
    sys.path.insert(0,str(Path.cwd()))
    from verifier.task003.campaign import grade
    r=grade(a.source,a.out,public=a.phase=='public',cases=json.loads(Path(a.inputs).read_text()))
    print(json.dumps({'reward':r['reward'],'category':r['category']}))

if __name__=='__main__':main()
