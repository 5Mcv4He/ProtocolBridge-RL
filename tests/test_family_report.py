import hashlib,json,tempfile,unittest
from pathlib import Path
from task_families.report import report,sha,ROOT
from environment.control_bank import bundle

class FamilyReport(unittest.TestCase):
 def test_source_and_bank_are_required(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'package';g=Path(tmp)/'gate';p.mkdir();g.mkdir();tid='example'
   files={'fixtures/reference.sv':b'module bridge(input logic clk); endmodule\n',
          'tasks/example/workspace/bridge.sv':b'module bridge; wire waiting; endmodule\n',
          'environment/control_bank.py':(ROOT/'environment/control_bank.py').read_bytes(),
          'tasks/example/task.json':json.dumps({'quality':{'references':['fixtures/reference.sv'],'negative_controls':[]}}).encode()}
   for name,data in files.items():
    dest=p/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
   hashes={k:sha(p/k) for k in files};manifest={'schema':'task-capsule-v1','task_id':tid,'files':hashes}
   (p/'family-manifest.json').write_text(json.dumps(manifest))
   (g/'freeze.json').write_text(json.dumps({'task_id':tid,'files':hashes,'toolchain':{}}))
   (g/'control_bank.sv').write_text(bundle([p/'fixtures/reference.sv']))
   value={'accepted':True,'task_id':tid,'freeze_sha256':sha(g/'freeze.json'),
          'positive_count':1,'negative_count':0,'mechanism_checks':1,'isolation_probe_accepted':True,'limitations':[],
          'results':{'reference':{'source_sha256':sha(g/'control_bank.sv'),'reward':1},
                     'initial':{'source_sha256':sha(p/'tasks/example/workspace/bridge.sv'),'reward':0}}}
   (g/'result.json').write_text(json.dumps(value))
   self.assertTrue(report(p,g)['accepted'])
   (g/'control_bank.sv').write_text('different compiler input')
   with self.assertRaises(ValueError):report(p,g)
   (g/'control_bank.sv').write_text(bundle([p/'fixtures/reference.sv']))
   value['results'].pop('reference');(g/'result.json').write_text(json.dumps(value))
   with self.assertRaises(ValueError):report(p,g)
