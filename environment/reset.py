import argparse,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def reset(work):
    work=Path(work); work.mkdir(parents=True,exist_ok=False)
    task=ROOT/'tasks/axil_to_apb4_001'
    shutil.copy(task/'spec.md',work/'spec.md')
    shutil.copy(task/'workspace/bridge.sv',work/'bridge.sv')
    return {'task':'axil_to_apb4_001','workspace':str(work)}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('workspace');a=p.parse_args();print(json.dumps(reset(a.workspace)))
