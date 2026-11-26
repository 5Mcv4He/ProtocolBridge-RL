import copy,unittest
from task_families.qualify_inputs import check_binding
class Qualification(unittest.TestCase):
 def test_exact_source_and_toolchain_binding(self):
  capsule={'task_id':'queue','files':{'verifier/a.py':'123','environment/b.py':'456'}}
  admission={'toolchain':{'vcs':'version'}}
  m={'task_id':'queue','source_files':{'verifier/a.py':'123','environment/b.py':'456'},'toolchain':{'vcs':'version'}}
  check_binding(capsule,admission,m)
  for key,value in [('task_id','other'),('source_files',{'verifier/a.py':'changed'}),('source_files',{}),('source_files',{'verifier/a.py':'123'}),('source_files',{'new.py':'123'}),('toolchain',{'vcs':'different'})]:
   bad=copy.deepcopy(m);bad[key]=value
   with self.assertRaises(ValueError):check_binding(capsule,admission,bad)
