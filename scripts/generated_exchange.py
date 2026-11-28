"""One export entry for qualified generated domains; preserve historical schemas.

Dispatch is by an explicit frozen study profile, never a Task ID or a module
name supplied by a task. Each domain keeps its own replay and grade audit.
"""
import argparse
import json
from pathlib import Path


def export(plan, runs, out):
    profile=json.loads(Path(plan).read_text()).get('schema')
    if profile=='native-router-package-study-v2':
        from scripts.package_exchange import export as implementation
    elif profile=='native-register-material-study-v1':
        from scripts.register_exchange import export as implementation
    elif profile=='native-composed-package-study-v1':
        from scripts.composed_exchange import export as implementation
    else:
        raise ValueError('Unsupported frozen generated-task study profile')
    return implementation(plan,runs,out)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('plan','runs','out'):p.add_argument(n)
    a=p.parse_args();print(json.dumps(export(a.plan,a.runs,a.out)))
