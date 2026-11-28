"""Deduplicate frozen source bytes only; never reuse binaries or verdicts.

Explicit trusted capsule roots are required. Editable Agent workspaces, run
outputs and Git checkouts are not inputs. Files become read-only; replacing a
file later breaks its link, while every evaluator still validates its SHA-256.
This is an operational storage optimization, not a security boundary.
"""
import argparse
import hashlib
import json
import os
import stat
import uuid
from pathlib import Path
from task_families.production_lock import exclusive
from task_families.router_v2.generate import sha, verify


def compact(packages, store):
    roots = [Path(p).resolve() for p in packages]; store = Path(store).resolve()
    if not roots or len(set(roots)) != len(roots): raise ValueError('Distinct explicit capsules required')
    if any(a == store or a in store.parents or store in a.parents for a in roots):
        raise ValueError('Store must be separate from capsule roots')
    if any(a in b.parents for a in roots for b in roots if a != b):
        raise ValueError('Overlapping capsules are not supported')
    manifests = []
    for root in roots:
        if (root/'.git').exists(): raise ValueError('Never compact a Git checkout')
        m = verify(root)
        if any((root/name).is_symlink() for name in m['files']): raise ValueError('Symlinked source not supported')
        manifests.append((root, m, sha(root/'family-manifest.json')))
    paths = [root/name for root,m,_ in manifests for name in m['files']]
    def allocation(items):
        seen = set(); blocks = 0
        for p in items:
            s = p.stat(); key = (s.st_dev,s.st_ino)
            if key not in seen: blocks += s.st_blocks*512; seen.add(key)
        return dict(unique_inodes=len(seen),allocated_bytes=blocks)
    before = allocation(paths)
    linked = 0
    with exclusive(store):
        for root,m,identity in manifests:
            for name,h in m['files'].items():
                p = root/name; mode = 0o444 | (stat.S_IMODE(p.stat().st_mode)&0o111)
                obj = store/h[:2]/(h+'-'+format(mode,'o')); obj.parent.mkdir(exist_ok=True)
                if not obj.exists():
                    raw = p.read_bytes()
                    if hashlib.sha256(raw).hexdigest()!=h: raise ValueError('Source changed while storing')
                    tmp = obj.with_name(obj.name+'.'+uuid.uuid4().hex)
                    with tmp.open('xb') as f: f.write(raw)
                    tmp.chmod(mode); tmp.replace(obj)
                if obj.is_symlink() or sha(obj)!=h or stat.S_IMODE(obj.stat().st_mode)!=mode:
                    raise ValueError('Content store object is corrupt or writable')
                if (p.stat().st_dev,p.stat().st_ino)==(obj.stat().st_dev,obj.stat().st_ino): continue
                if sha(p)!=h: raise ValueError('Source changed before replacement')
                tmp = p.with_name('.pb-source-link-'+uuid.uuid4().hex)
                os.link(str(obj),str(tmp)); tmp.replace(p); linked += 1
            if sha(root/'family-manifest.json')!=identity: raise ValueError('Manifest changed')
            verify(root)
    after = allocation(paths)
    return dict(schema='frozen-source-storage-v1',capsules=len(roots),source_entries=len(paths),
                links_created=linked,before=before,after=after,
                source_bytes_unchanged=True,
                manifest_sha256=[h for _,_,h in manifests],
                scope='Frozen source storage only. Allocated bytes count unique selected source inodes; directory entries, store metadata and archives are excluded. No simulation, reward, binary-cache or admission reuse.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--store',required=True);p.add_argument('--out',required=True)
    p.add_argument('packages',nargs='+');a=p.parse_args()
    if Path(a.out).exists(): raise ValueError('Do not overwrite storage evidence')
    r=compact(a.packages,a.store)
    with Path(a.out).open('x') as f:json.dump(r,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in r.items() if k!='manifest_sha256'}))
