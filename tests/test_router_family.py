import copy,json,tempfile,unittest,subprocess,sys
from pathlib import Path
from task_families.router_v1.generate import validate,generate,verify,ROOT
class RouterFamily(unittest.TestCase):
 def test_invalid_contracts(self):
  c=json.loads((ROOT/'task_families/router_v1/configurations.json').read_text())['instances'][0]
  for windows in ([[[4096,4096]]],[[4096,True],[12288,8192],[36864,4096]],[[4096,8192],[4096,4096],[36864,4096]],[[0,4096],[12288,8192],[36864,4096]],[[4096,4096],[61440,4096],[36864,4096]]):
   bad=copy.deepcopy(c);bad['windows']=windows
   with self.assertRaises(ValueError):validate(bad)
 def test_capsule_contract_and_tamper(self):
  c=json.loads((ROOT/'task_families/router_v1/configurations.json').read_text())['instances'][2]
  with tempfile.TemporaryDirectory() as tmp:
   out=Path(tmp)/'capsule';generate(c,out);m=verify(out)
   self.assertEqual(m['task_id'],c['task_id'])
   second=Path(tmp)/'repeat';generate(c,second)
   self.assertEqual(m,verify(second))
   self.assertEqual((out/'family-manifest.json').read_bytes(),(second/'family-manifest.json').read_bytes())
   code='from verifier.task002.scenarios import target,suite; assert target(0x1ffc)==0; assert target(0x2000)==1; assert target(0x4000)==-1; assert target(0x40002000)==2; assert len(suite(True))==22; assert suite(True)[0]["name"]=="address_data"; assert suite(True)[-1]["name"]=="generated_boundaries"; from environment.check_baseline import check; assert check()["status"]=="pass"'
   subprocess.run([sys.executable,'-c',code],cwd=str(out),check=True)
   spec=(out/'tasks'/c['task_id']/'spec.md').read_text();self.assertIn('0x00002000–0x00003fff',spec)
   with self.assertRaises(ValueError):generate(c,out)
   p=out/'verifier/task002/vip.sv';p.write_text(p.read_text().replace("32'h1fff","32'h2fff"))
   with self.assertRaises(ValueError):verify(out)

 def test_irregular_interior_is_exercised_not_only_oracle_checked(self):
  c=json.loads((ROOT/'task_families/router_v1/configurations.json').read_text())['instances'][1]
  with tempfile.TemporaryDirectory() as tmp:
   out=Path(tmp)/'capsule';generate(c,out)
   code="from verifier.task002.scenarios import suite; rows=next(c['rows'] for c in suite() if c['name']=='generated_boundaries'); assert all((kind,a) in {(r[0],r[1]) for r in rows} for kind in (0,1) for a in (0x21ffc,0x22000,0x22004,0x22ffc,0x23000)); import json; m=json.load(open('tasks/x2p_router_irregular_v1/task.json')); assert len(m['quality']['negative_controls'])==14"
   subprocess.run([sys.executable,'-c',code],cwd=str(out),check=True)
