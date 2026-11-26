"""Verify trusted generated source capsules; this is integrity, not admission."""
import hashlib,json
from pathlib import Path

def verify(package):
 root=Path(package).resolve();m=json.loads((root/'family-manifest.json').read_text())
 if m.get('schema')=='router-capsule-v1':
  from task_families.router_v1.generate import verify as legacy
  return legacy(root)
 if m.get('schema')!='task-capsule-v1':raise ValueError('Unsupported capsule schema')
 for name,h in m['files'].items():
  p=Path(name)
  try:(root/p).resolve().relative_to(root)
  except ValueError:raise ValueError('Capsule path escapes root')
  if p.is_absolute() or '..' in p.parts or (root/p).is_symlink() or hashlib.sha256((root/p).read_bytes()).hexdigest()!=h:raise ValueError('Changed capsule file: '+name)
 for d in ('environment','verifier','fixtures','tasks','tests','scripts'):
  for p in (root/d).rglob('*'):
   if p.is_file() and '__pycache__' not in p.parts and str(p.relative_to(root)) not in m['files']:raise ValueError('Extra executable source')
 return m
