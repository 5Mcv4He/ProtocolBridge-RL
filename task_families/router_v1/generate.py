"""Bounded source specialization, not a universal HDL or verifier generator.
Produces an isolated repository capsule; original tasks and evidence are untouched.
"""
import argparse,hashlib,io,json,re,subprocess,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE_COMMIT='194ffbe181601e4876035a35bfa49e7242317d41'
OLD='axil_to_apb4_router_002'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def validate(c):
 if set(c)!={'task_id','windows','purpose'} or not re.fullmatch('x2p_router_[a-z]+_v1',c['task_id']):raise ValueError('Invalid identity or fields')
 w=c['windows']
 if not isinstance(w,list) or len(w)!=3:raise ValueError('Exactly three lanes are supported')
 for row in w:
  if not isinstance(row,list) or len(row)!=2 or any(type(v)!=int for v in row):raise ValueError('Integer [base,size] required')
  b,n=row
  if b<4096 or n not in (4096,8192,12288) or b%4096 or b+n>=2**32:raise ValueError('Unsupported aligned range')
 if w[0][0]+w[0][1]>=2**31:raise ValueError('Lane zero must allow the inherited high-bit alias control')
 for i,(b,n) in enumerate(w):
  for a,m in w[:i]:
   if max(b,a)<min(b+n,a+m):raise ValueError('Overlapping windows')
 if any(b<=0xf000<b+n for b,n in w):raise ValueError('Reserved unmapped reset address')
 return c

def generate(c,out):
 validate(c);out=Path(out).resolve()
 approved=json.loads((Path(__file__).with_name('configurations.json')).read_text())['instances']
 if c not in approved:raise ValueError('v1 supports only the three reviewed contracts')
 checks=json.loads(Path(__file__).with_name('oracle_checks.json').read_text())[c['task_id']]
 if out.exists():raise ValueError('Never overwrite a generated package')
 commit=subprocess.check_output(['git','rev-parse',BASE_COMMIT+'^{commit}'],cwd=str(ROOT),universal_newlines=True).strip()
 archive=subprocess.check_output(['git','archive',commit],cwd=str(ROOT));out.mkdir(parents=True)
 with tarfile.open(fileobj=io.BytesIO(archive)) as t:
  for member in t.getmembers():
   if member.issym() or member.islnk() or member.name.startswith('/') or '..' in Path(member.name).parts:raise ValueError('Unsafe source archive')
  t.extractall(str(out))
 original={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}
 # Bind the existing single-task adapters to a new identity inside this capsule.
 (out/'tasks'/OLD).rename(out/'tasks'/c['task_id'])
 for directory in ('environment','scripts','tasks','tests'):
  for p in (out/directory).rglob('*'):
   if p.is_file() and p.suffix in ('.py','.json','.md'):
    s=p.read_text()
    if OLD in s:p.write_text(s.replace(OLD,c['task_id']))
 registry=json.loads((out/'tasks/registry.json').read_text());registry['tasks']=[t for t in registry['tasks'] if t['task_id']==c['task_id']]
 registry['tasks'][0]['title']=c['purpose'];(out/'tasks/registry.json').write_text(json.dumps(registry,indent=2)+'\n')
 old=[(0x1000,0x1000),(0x8000,0x2000),(0x40000000,0x1000)];mapping={}
 for (b,n),(a,m) in zip(old,c['windows']):mapping.update({b:a,b+n:a+m,b+n-1:a+m-1})
 # Reference implementations use exclusive upper bounds. Preserve each inherited fault.
 for p in (out/'fixtures/task002').glob('*.sv'):
  s=p.read_text();p.write_text(re.sub(r"(3[12]'h)([0-9a-fA-F]+)",lambda m:m[1]+format(mapping.get(int(m[2],16),int(m[2],16)),'x'),s))
 # Independent SV oracle uses inclusive endpoints, not the RTL decoder function.
 p=out/'verifier/task002/vip.sv';s=p.read_text()
 decode='function automatic int expected_target(bit[31:0] a);\n'+''.join(" if(a inside {[32'h%x:32'h%x]}) return %d;\n"%(b,b+n-1,i) for i,(b,n) in enumerate(c['windows']))+' return -1;\nendfunction'
 s,n=re.subn(r'function automatic int expected_target\(bit\[31:0\] a\);.*?endfunction',decode,s,flags=re.S);assert n==1
 local='function automatic bit[31:0] expected_local(bit[31:0] a);\n case(expected_target(a))\n'+''.join(" %d:return a-32'h%x;\n"%(i,b) for i,(b,_) in enumerate(c['windows']))+' default:return 0;\n endcase\nendfunction'
 s,n=re.subn(r'function automatic bit\[31:0\] expected_local\(bit\[31:0\] a\);.*?endfunction',local,s,flags=re.S);assert n==1;p.write_text(s)
 # Hand-reviewed semantic anchors are independent of both decoder generators.
 tb=out/'verifier/task002/tb.sv';text=tb.read_text();probe='\n initial begin\n'
 for address,lane,offset in checks:
  probe+=" if(expected_target(32'h%s)!=%d || expected_local(32'h%s)!=32'd%d) `uvm_fatal(\"PB_INFRA\",\"Generated oracle differs from reviewed contract\")\n"%(address,lane,address,offset)
 probe+=' $display("PB_ROUTER_ORACLE_OK");\n end\n'
 tb.write_text(text.replace('module tb;','module tb;'+probe))
 campaign=out/'verifier/task002/campaign.py';text=campaign.read_text();text=text.replace("if 'PB_INFRA' in log or","if 'PB_ROUTER_ORACLE_OK' not in log or 'PB_INFRA' in log or");campaign.write_text(text)
 # Keep stimulus history as a private component; a new independent adapter remaps
 # only mapped protocol traffic and constructs a fresh boundary/alias suite.
 p=out/'verifier/task002/scenarios.py';p.rename(p.with_name('_protocol_template.py'))
 template=(ROOT/'task_families/router_v1/scenarios.py.in').read_text();p.write_text(template.replace('WINDOWS_VALUE',repr(tuple(tuple(v) for v in c['windows']))))
 task=out/'tasks'/c['task_id'];p=task/'spec.md';s=p.read_text().replace('task 002, revision 1',c['task_id']+' — family v1')
 for i,((b,n),(a,m)) in enumerate(zip(old,c['windows'])):
  s=s.replace('| %d | 0x%08x–0x%08x | AXI address minus 0x%08x |'%(i,b,b+n-1,b),'| %d | 0x%08x–0x%08x | AXI address minus 0x%08x |'%(i,a,a+m-1,a))
 p.write_text(s)
 m=json.loads((task/'task.json').read_text());m['family']={'id':'x2p_three_target_router_v1','parameters':c,'base_commit':commit,'generator_sha256':sha(Path(__file__)),'semantic_anchors_sha256':sha(Path(__file__).with_name('oracle_checks.json'))};m['quality']['required_requirements']+=['G_RANGE_EDGES','G_ADDRESS_ALIAS']
 m['quality']['spec_review']['bounds']='Generated full 32-bit nonoverlapping ranges; independent boundary and alias checks; inherited timing bounds'
 (task/'task.json').write_text(json.dumps(m,indent=2)+'\n')
 (task/'README.md').write_text('# '+c['task_id']+'\n\n'+c['purpose']+'\n\nGenerated parameterized contract; three lanes, one global outstanding transaction. This is not a new protocol or independent ability count. See [Spec](spec.md) and task.json. Candidate only until its source-bound gate passes.\n')
 (out/'README.md').write_text('# Generated router task capsule\n\nTask: '+c['task_id']+'\n\nSee tasks/'+c['task_id']+'/spec.md and family-manifest.json. Candidate until source-bound gate acceptance. Inherited module names task002 denote reusable backend slots, not the historical task identity.\n')
 files={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}
 manifest={'schema':'router-capsule-v1','task_id':c['task_id'],'parameters':c,'source_commit':commit,'generator_sha256':sha(Path(__file__)),'scenario_template_sha256':sha(ROOT/'task_families/router_v1/scenarios.py.in'),'files':files,'changed_files':[k for k,v in files.items() if original.get(k)!=v],'status':'candidate_not_admitted'}
 (out/'family-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 subprocess.run(['git','init','-q',str(out)],check=True)
 subprocess.run(['git','add','.'],cwd=str(out),check=True)
 subprocess.run(['git','-c','user.name=ProtocolBridge Generator','-c','user.email=generator@example.invalid','commit','-qm','Generated router contract '+c['task_id']],cwd=str(out),check=True)
 return {'task_id':c['task_id'],'package':str(out),'manifest_sha256':sha(out/'family-manifest.json')}

def verify(package):
 root=Path(package).resolve();m=json.loads((root/'family-manifest.json').read_text())
 if m['schema']!='router-capsule-v1':raise ValueError('Unsupported package')
 for name,h in m['files'].items():
  p=Path(name)
  if p.is_absolute() or '..' in p.parts or sha(root/p)!=h:raise ValueError('Package changed: '+name)
 for d in ('environment','verifier','fixtures','tasks','tests','scripts'):
  for p in (root/d).rglob('*'):
   if p.is_file() and '__pycache__' not in str(p) and str(p.relative_to(root)) not in m['files']:raise ValueError('Extra runtime file')
 return m
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('instance');p.add_argument('out');a=p.parse_args()
 entries=json.loads((Path(__file__).with_name('configurations.json')).read_text())['instances'];c=next(x for x in entries if x['task_id']==a.instance)
 print(json.dumps(generate(c,a.out),indent=2))
