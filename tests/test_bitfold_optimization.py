import tempfile,unittest
from pathlib import Path
from verifier.bitfold_optimization.campaign import measurement,LIBRARY_SHA256
from environment.artifact_task.session_v6 import project_measurement,Session
from environment.artifact_task.session_v4 import sha
class Optimization(unittest.TestCase):
 def base(self):return dict(reward=1,verification_complete=True,library_sha256=LIBRARY_SHA256,**{k:{'reward':1} for k in ('integer_oracle','synthesis','independent_reference','own_netlist')})
 def test_function_and_complete_measurement_required(self):
  b=self.base();self.assertEqual(measurement(b,'PB_CELLS=22\n')['mapped_cell_count'],22)
  for log in ('','PB_CELLS=22\nPB_CELLS=22\n'):
   with self.assertRaises(ValueError):measurement(b,log)
  b['library_sha256']='other'
  with self.assertRaises(ValueError):measurement(b,'PB_CELLS=22\n')
  b=self.base();b['own_netlist']['reward']=None
  with self.assertRaises(ValueError):measurement(b,'PB_CELLS=22\n')
  b['reward']=0;self.assertIsNone(measurement(b,'PB_CELLS=0\n'))
 def test_projection_never_returns_sensitive_fields(self):
  m=measurement(self.base(),'PB_CELLS=23\n');m.update(private_vector='secret',log='/private/path',extra={'secret':1})
  self.assertEqual(project_measurement(m),{'mapped_cell_count':23,'limit':22,'functional_checks_passed':True})
  for bad in ('23',True,-1,1000001):
   with self.assertRaises(ValueError):project_measurement(dict(m,mapped_cell_count=bad))
 def test_candidate_binding_budgets_and_submit_preserved(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);w=root/'work';w.mkdir();(w/'spec.md').write_text('fixed');(w/'bitfold.sv').write_text('initial');calls=[]
   def grade(p,out,phase):
    calls.append(sha(p));return {'reward':0.,'category':'synthesis_error','source_sha256':sha(p),'resource_measurement':measurement(self.base(),'PB_CELLS=23\n')}
   s=Session({'task_id':'bitfold_cell_budget_v1','deliverable':'bitfold.sv'},w,root/'session',grade,20,2)
   for f in ('spec.md','bitfold.sv'):s.handle({'tool':'read','file':f})
   first=s.handle({'tool':'test'});s.handle({'tool':'edit','content':'new'});second=s.handle({'tool':'test'})
   self.assertNotEqual(first['source_sha256'],second['source_sha256']);self.assertEqual(first['measurement']['mapped_cell_count'],23)
   self.assertEqual(s.handle({'tool':'test'})['status'],'REJECTED');self.assertEqual(len(calls),2)
   s.handle({'tool':'submit'});self.assertEqual(s.handle({'tool':'edit','content':'other'})['status'],'REJECTED')
   self.assertEqual((root/'session/submission/bitfold.sv').read_text(),'new')
 def test_total_budget_cannot_be_bypassed(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);w=root/'w';w.mkdir();(w/'spec.md').write_text('x');(w/'bitfold.sv').write_text('x');calls=[]
   s=Session({'task_id':'bitfold_cell_budget_v1','deliverable':'bitfold.sv'},w,root/'s',lambda *a:calls.append(a),20,4)
   for _ in range(20):s.handle({'tool':'unknown'})
   self.assertEqual(s.handle({'tool':'test'})['reason'],'episode_closed');self.assertEqual(calls,[])
if __name__=='__main__':unittest.main()
