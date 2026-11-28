"""Derive complete frozen input roles from a trusted, verified composed capsule.

Run as a subprocess from the capsule directory to avoid Python module-cache
collisions between instances. This entry is never exposed to the solving Agent.
"""
import json,sys
from pathlib import Path

ROLES=('public','terminal','heldout')

def seeds_checked(seeds):
    if (not isinstance(seeds,dict) or set(seeds)!=set(ROLES)
            or any(type(v) is not int or not 0<=v<2**31 for v in seeds.values())):
        raise ValueError('Explicit bounded integer seed required for each input role')
    if len(set(seeds.values())) != 3:raise ValueError('Distinct role seeds required')
    return dict(seeds)

if __name__=='__main__':
    seeds=seeds_checked(json.loads(sys.argv[1]))
    sys.path.insert(0,str(Path.cwd()))
    from verifier.task003.scenarios import suite
    print(json.dumps({role:suite(role=='public',seeds[role]) for role in ROLES}))
