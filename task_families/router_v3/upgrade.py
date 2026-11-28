"""New qualification revision; preserves the complete original capsule and evidence.

Only the trusted control driver changes. DUT, VIP, Scoreboard, input generators,
Spec, initial materials and campaign judgment are byte-identical to the parent.
"""
import argparse,json,shutil
from pathlib import Path
from task_families.router_v2.generate import verify,sha

def upgrade(parent,out):
    parent=Path(parent).resolve();out=Path(out).resolve();m=verify(parent)
    if m.get('family')!='x2p_three_target_router_v3' or m.get('qualification_revision') is not None:raise ValueError('Expected original execution adapter v1 capsule')
    if out.exists():raise ValueError('Never overwrite a capsule')
    out.mkdir(parents=True)
    for name in m['files']:
        p=out/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(str(parent/name),str(p))
    driver=Path(__file__).with_name('qualification_v2.py');name='task_families/router_v3/qualification_v2.py'
    shutil.copyfile(str(driver),str(out/name))
    files=dict(m['files']);files[name]=sha(driver)
    new=dict(m,files=files,qualification_revision=2,qualification_parent_manifest_sha256=sha(parent/'family-manifest.json'),qualification_upgrade_sha256=sha(Path(__file__)))
    (out/'family-manifest.json').write_text(json.dumps(new,indent=2,sort_keys=True)+'\n')
    verify(out)
    return new

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('parent');p.add_argument('out');a=p.parse_args();print(upgrade(a.parent,a.out)['task_id'])
