"""Small shared production steps; semantic specialization remains family-owned.
Historical producers are unchanged. Capsules are trusted source, not sandboxed plugins.
"""
import hashlib,io,json,re,shutil,subprocess,sys,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE='194ffbe181601e4876035a35bfa49e7242317d41'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):Path(p).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def start(out,old,task):
 out=Path(out).resolve()
 if out.exists():raise ValueError('Never overwrite a source capsule')
 data=subprocess.check_output(['git','archive',BASE],cwd=str(ROOT));out.mkdir(parents=True)
 with tarfile.open(fileobj=io.BytesIO(data)) as t:
  if any(m.issym() or m.islnk() or m.name.startswith('/') or '..' in Path(m.name).parts for m in t.getmembers()):raise ValueError('Unsafe source archive')
  t.extractall(str(out))
 baseline=json.loads((out/'tasks/axil_to_apb4_001/baseline.json').read_text())
 keep={Path(k).parts[1] for k in baseline['evidence_files'] if k.startswith('experiments/')}
 for p in (out/'experiments').iterdir():
  if p.name not in keep:
   shutil.rmtree(str(p)) if p.is_dir() else p.unlink()
 shutil.rmtree(str(out/'docs'));(out/'tasks'/old).rename(out/'tasks'/task)
 for directory in ('environment','scripts','tasks','tests'):
  for p in (out/directory).rglob('*'):
   if p.is_file() and p.suffix in ('.py','.json','.md'):
    text=p.read_text()
    if old in text:p.write_text(text.replace(old,task))
 reg=json.loads((out/'tasks/registry.json').read_text());reg['tasks']=[x for x in reg['tasks'] if x['task_id']==task];write(out/'tasks/registry.json',reg)
 return out

def finish(out,task,family,parameters,producer_files):
 out=Path(out);subprocess.run([sys.executable,'-m','compileall','-q','environment','verifier','scripts','tests'],cwd=out,check=True)
 result=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-q'],cwd=out,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 (out/'.local').mkdir(exist_ok=True);(out/'.local/generation-tests.log').write_bytes(result.stdout)
 if result.returncode:raise RuntimeError('Runtime tests failed; candidate preserved')
 for source in producer_files:
  saved=out/'.local/producer-source'/source.relative_to(ROOT);saved.parent.mkdir(parents=True,exist_ok=True);saved.write_bytes(source.read_bytes())
 write(out/'generation-check.json',{'passed':True,'count':int(re.search(rb'Ran (\d+) tests',result.stdout).group(1))})
 files={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file() and '.git' not in p.relative_to(out).parts and p.name!='family-manifest.json' and '__pycache__' not in p.parts and '.local' not in p.relative_to(out).parts}
 m={'schema':'task-capsule-v1','family':family,'task_id':task,'source_commit':BASE,'parameters':parameters,'producer_files':{str(p.relative_to(ROOT)):sha(p) for p in sorted(producer_files)},'files':files,'status':'candidate_not_admitted'};write(out/'family-manifest.json',m)
 subprocess.run(['git','init','-q',str(out)],check=True);subprocess.run(['git','add','.'],cwd=out,check=True);subprocess.run(['git','-c','user.name=ProtocolBridge Generator','-c','user.email=generator@example.invalid','commit','-qm','Generated '+task],cwd=out,check=True)
 return m
