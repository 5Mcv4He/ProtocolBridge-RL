import json,tempfile,unittest
from pathlib import Path
from environment.artifact_task.session import Session,sha
class ArtifactSession(unittest.TestCase):
 def test_permissions_budget_versions_and_stop(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);work=root/'work';work.mkdir();(work/'spec.md').write_text('Spec');(work/'accumulator.sv').write_text('old')
   calls=[]
   def grade(p,out,phase):
    calls.append((sha(p),phase));return {'reward':0.,'category':'not_equivalent','source_sha256':sha(p),'secret':'not visible'}
   s=Session({'task_id':'x','deliverable':'accumulator.sv'},work,root/'out',grade,max_actions=12,max_tests=2)
   self.assertEqual(s.handle({'tool':'read','file':'../reference.sv'})['reason'],'file_not_allowed')
   for file in ('spec.md','accumulator.sv'):s.handle({'tool':'read','file':file})
   first=s.handle({'tool':'test'});s.handle({'tool':'edit','content':'new'});second=s.handle({'tool':'test'})
   self.assertNotEqual(first['source_sha256'],second['source_sha256']);self.assertNotIn('secret',second)
   self.assertEqual(s.handle({'tool':'test'})['reason'],'test_budget_exhausted');self.assertEqual(len(calls),2)
   s.handle({'tool':'submit'});self.assertEqual(len(calls),2)
   self.assertEqual(s.handle({'tool':'edit','content':'tamper'})['reason'],'episode_closed')
   with self.assertRaises(ValueError):s.finalize(False)
   self.assertEqual(s.finalize(True)['reward'],0);self.assertEqual(calls[-1][1],'terminal')
 def test_total_action_limit(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);(p/'spec.md').write_text('s');(p/'x.json').write_text('{}')
   def forbidden(*a):raise AssertionError('Must never execute')
   s=Session({'task_id':'x','deliverable':'x.json'},p,p/'out',forbidden,max_actions=3,max_tests=1)
   for _ in range(3):s.handle({})
   self.assertEqual(s.handle({'tool':'test'})['reason'],'episode_closed');self.assertEqual(s.actions,3)
