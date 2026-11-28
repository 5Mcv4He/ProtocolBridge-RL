"""A new legal aperture contract uses the shared router renderer, not a Task-ID list."""
import argparse,json
from task_families.router_core import generate
from . import contract
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('contract');p.add_argument('out');a=p.parse_args()
    print(json.dumps(generate(json.loads(open(a.contract).read()),a.out,contract),indent=2))
