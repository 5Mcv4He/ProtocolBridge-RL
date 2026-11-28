"""Bounded source specialization, not a universal HDL or verifier generator.
Produces an isolated repository capsule; original tasks and evidence are untouched.
"""
import argparse,hashlib,io,json,re,subprocess,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE_COMMIT='194ffbe181601e4876035a35bfa49e7242317d41'
OLD='axil_to_apb4_router_002'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def generate(c,out,profile):
 profile.validate(c);out=Path(out).resolve()
 checks=profile.anchors(c)
 if out.exists():raise ValueError('Never overwrite a generated package')
 commit=subprocess.check_output(['git','rev-parse',BASE_COMMIT+'^{commit}'],cwd=str(ROOT),universal_newlines=True).strip()
 archive=subprocess.check_output(['git','archive',commit],cwd=str(ROOT));out.mkdir(parents=True)
 with tarfile.open(fileobj=io.BytesIO(archive)) as t:
  for member in t.getmembers():
   if member.issym() or member.islnk() or member.name.startswith('/') or '..' in Path(member.name).parts:raise ValueError('Unsafe source archive')
  t.extractall(str(out))
 original={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()}
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
 # Newly enlarged interiors need a fault control independent of old address edges.
 lane=max(range(3),key=lambda i:c['windows'][i][1]);base,size=c['windows'][lane]
 mask=((1<<(size-1).bit_length())-1)&~0x1000
 ref=(out/'fixtures/task002/reference.sv').read_text();needle="local_address=a-32'h%x;"%base
 assert ref.count(needle)==1
 (out/'fixtures/task002/bad_local_bit12.sv').write_text(ref.replace(needle,"local_address=(a-32'h%x) & 32'h%x;"%(base,mask)))
 # Independent SV oracle uses inclusive endpoints, not the RTL decoder function.
 p=out/'verifier/task002/vip.sv';s=p.read_text()
 decode='function automatic int expected_target(bit[31:0] a);\n'+''.join(" if(a inside {[32'h%x:32'h%x]}) return %d;\n"%(b,b+n-1,i) for i,(b,n) in enumerate(c['windows']))+' return -1;\nendfunction'
 s,n=re.subn(r'function automatic int expected_target\(bit\[31:0\] a\);.*?endfunction',decode,s,flags=re.S);assert n==1
 local='function automatic bit[31:0] expected_local(bit[31:0] a);\n case(expected_target(a))\n'+''.join(" %d:return a-32'h%x;\n"%(i,b) for i,(b,_) in enumerate(c['windows']))+' default:return 0;\n endcase\nendfunction'
 s,n=re.subn(r'function automatic bit\[31:0\] expected_local\(bit\[31:0\] a\);.*?endfunction',local,s,flags=re.S);assert n==1;p.write_text(s)
 # Enumerated occupancy anchors are independent of RTL and SV interval decoders.
 tb=out/'verifier/task002/tb.sv';text=tb.read_text();probe='\n initial begin\n'
 for address,lane,offset in checks:
  probe+=" if(expected_target(32'h%s)!=%d || expected_local(32'h%s)!=32'd%d) `uvm_fatal(\"PB_INFRA\",\"Generated oracle differs from enumerated occupancy\")\n"%(address,lane,address,offset)
 probe+=' $display("PB_ROUTER_ORACLE_OK");\n end\n'
 tb.write_text(text.replace('module tb;','module tb;'+probe))
 campaign=out/'verifier/task002/campaign.py';text=campaign.read_text();text=text.replace("if 'PB_INFRA' in log or","if 'PB_ROUTER_ORACLE_OK' not in log or 'PB_INFRA' in log or");campaign.write_text(text)
 # Keep stimulus history as a private component; a new independent adapter remaps
 # only mapped protocol traffic and constructs a fresh boundary/alias suite.
 p=out/'verifier/task002/scenarios.py';p.rename(p.with_name('_protocol_template.py'))
 template=(ROOT/'task_families/router_v1/scenarios.py.in').read_text();p.write_text(template.replace('WINDOWS_VALUE',repr(tuple(tuple(v) for v in c['windows']))).replace('REVIEWED_ADDRESSES_VALUE',repr(tuple(int(a,16) for a,_,_ in checks))))
 (out/'obligations.json').write_text(json.dumps(profile.obligations(c),indent=2)+'\n')
 task=out/'tasks'/c['task_id'];p=task/'spec.md';s=p.read_text().replace('task 002, revision 1',c['task_id']+' — family v1')
 for i,((b,n),(a,m)) in enumerate(zip(old,c['windows'])):
  s=s.replace('| %d | 0x%08x–0x%08x | AXI address minus 0x%08x |'%(i,b,b+n-1,b),'| %d | 0x%08x–0x%08x | AXI address minus 0x%08x |'%(i,a,a+m-1,a))
 p.write_text(s)
 m=json.loads((task/'task.json').read_text());m['family']={'id':profile.FAMILY,'parameters':c,'base_commit':commit,'generator_sha256':sha(Path(__file__)),'semantic_anchors_sha256':sha(profile.SOURCE)};m['quality']['required_requirements']+=['G_RANGE_EDGES','G_ADDRESS_ALIAS','G_OFFSET_CARRY']
 for negative in m['quality']['negative_controls']:
  if negative['source'].endswith('bad_address_alias.sv'):negative['first_case']='generated_boundaries'
 m['quality']['negative_controls'].append({'source':'fixtures/task002/bad_local_bit12.sv','first_case':'generated_boundaries','violation':'Drops local-address bit 12 inside a window of at least 8 KiB; violates exact global-minus-base translation.'})
 m['quality']['minimum_negative_controls']=14
 profile.augment(out,c,m)
 m['quality']['spec_review']['bounds']='Generated full 32-bit nonoverlapping ranges; independent boundary and alias checks; inherited timing bounds'
 (task/'task.json').write_text(json.dumps(m,indent=2)+'\n')
 (task/'README.md').write_text("""# {task}

This task asks an Agent to implement a three-target AXI4-Lite → APB4 bridge.
The bridge decodes a global address, selects one peripheral, converts the address
to that peripheral's local offset, and returns its response. Unmapped requests
must return DECERR without an APB transfer.

**Why this instance:** {purpose}

The exact address table, timing, reset and unsupported behavior are in the
[Spec](spec.md). The fixed interface and initial implementation are in
[bridge.sv](workspace/bridge.sv). Three targets and one global outstanding
transaction remain fixed; this is a parameterized contract, not a new protocol.

## Verification and use

The trusted side uses active industrial VIP plus an independent UVM transaction
Scoreboard. Two legal references, {negative_count} requirement-violating controls and
enumerated occupancy anchors exercise the verifier; simulation remains finite.
[task.json](task.json) identifies the backend, requirements and controls.

From the capsule root, use `python3 scripts/tasks.py reset {task} .local/work`.
The same entry supports `test`, `submit`, `quality` and `rollout`. Industrial
execution requires a separately configured trusted backend. Agent access is
restricted to the chosen Policy; its own public tests do not set terminal reward.

This source package is **candidate-only**. A matching complete quality gate must
pass before a formal rollout. [The package manifest](../../family-manifest.json)
binds the generator, base commit and source hashes; no prior task's admission is
inherited. Original frozen evidence is retained separately.
""".format(task=c['task_id'],purpose=c['purpose'],negative_count=len(m['quality']['negative_controls'])))
 (out/'README.md').write_text('# Generated router task capsule\n\nThis capsule specializes an independently validated platform into one registered address contract. Start with the [task introduction](tasks/'+c['task_id']+'/README.md), then its Spec.\n\nUse the declared scripts/tasks.py reset/test/submit/quality/rollout entry points. Source generation does not confer admission. The [manifest](family-manifest.json) records provenance; each actual gate binds its own source and toolchain.\n\nInherited module names task002 denote reusable backend slots, not the historical task identity. Archived research utilities retain their original scope; they are not a general multi-package API.\n')
 # Specialize inherited unit contracts, never silently discard their failures.
 p=out/'tests/test_router002.py';text=p.read_text()
 text=re.sub(r'  for a,t in \[.*?\]:self.assertEqual\(target\(a\),t\)', '  for a,t in '+repr([(int(a,16),lane) for a,lane,_ in checks])+':self.assertEqual(target(a),t)',text)
 text=text.replace('len(suite(True)),21','len(suite(True)),22').replace('len(suite()),26','len(suite()),27')
 text=text.replace("log='PB2_SEQUENCE", "log='PB_ROUTER_ORACLE_OK\\nPB2_SEQUENCE")
 text=text.replace('r=interpret(log,0,c);self.assertEqual',"r=interpret('PB_ROUTER_ORACLE_OK\\n'+log,0,c);self.assertEqual")
 p.write_text(text)
 p=out/'tests/test_task_quality.py';text=p.read_text().replace("if c['name']=='decode_misses');addresses", "if c['name']=='generated_boundaries');addresses");p.write_text(text)
 # Output remains candidate-only if this subprocess fails. No EDA or API here.
 import sys
 test=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-q'],cwd=str(out),stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 (out/'.local').mkdir(exist_ok=True)
 (out/'.local/generation-unit-tests.log').write_bytes(test.stdout)
 if test.returncode:raise RuntimeError('Generated package unit tests failed; preserve directory for diagnosis')
 (out/'generation-check.json').write_text(json.dumps({'unit_tests_passed':True,'count':int(re.search(rb'Ran (\d+) tests',test.stdout).group(1))},indent=2)+'\n')
 files={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file() and '__pycache__' not in str(p) and '.local' not in p.relative_to(out).parts}
 manifest={'schema':'router-capsule-v1','task_id':c['task_id'],'parameters':c,'source_commit':commit,'generator_sha256':sha(Path(__file__)),'scenario_template_sha256':sha(ROOT/'task_families/router_v1/scenarios.py.in'),'files':files,'changed_files':[k for k,v in files.items() if original.get(k)!=v],'status':'candidate_not_admitted'}
 manifest['producer_files']={str(f.relative_to(ROOT)):sha(f) for f in [Path(__file__),profile.SOURCE,ROOT/'task_families/router_v1/scenarios.py.in']}
 manifest['family']=profile.FAMILY
 (out/'family-manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
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
