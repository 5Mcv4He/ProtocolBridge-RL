import json,tempfile,unittest
from pathlib import Path
from environment.artifact_task.session_v4 import Session,sha

class ResourceSessionTests(unittest.TestCase):
 def session(self,t,category='synthesis_error'):
  root=Path(t);work=root/'work';work.mkdir();(work/'spec.md').write_text('finite spec');(work/'bitfold.sv').write_text('initial')
  calls=[]
  def grade(p,o,phase):
   calls.append((sha(p),phase));return dict(reward=0.,category=category,source_sha256=sha(p),private_vector='SECRET',log='/secret/path',case='HIDDEN')
  s=Session({'task_id':'fixture','deliverable':'bitfold.sv'},work,root/'session',grade,20,4)
  return s,calls
 def test_whitelist_and_synthesis_category(self):
  with tempfile.TemporaryDirectory() as t:
   s,calls=self.session(t);obs=s.handle({'tool':'test'})
   self.assertEqual(set(obs),{'status','category','source_sha256','remaining_test_calls'})
   self.assertEqual(obs['category'],'synthesis_error');self.assertNotIn('SECRET',json.dumps(obs))
 def test_twenty_shared_actions_and_four_tests(self):
  with tempfile.TemporaryDirectory() as t:
   s,calls=self.session(t)
   for _ in range(4):self.assertEqual(s.handle({'tool':'test'})['status'],'FAIL')
   self.assertEqual(s.handle({'tool':'test'})['reason'],'test_budget_exhausted');self.assertEqual(len(calls),4)
   for _ in range(15):s.handle({'tool':'invalid'})
   self.assertTrue(s.done);self.assertEqual(s.actions,20)
   self.assertEqual(s.handle({'tool':'test'})['reason'],'episode_closed');self.assertEqual(len(calls),4)
 def test_unknown_category_projects_to_environment_error(self):
  with tempfile.TemporaryDirectory() as t:
   s,calls=self.session(t,'private_internal_detail');obs=s.handle({'tool':'test'})
   self.assertEqual(obs['status'],'ENV_ERROR');self.assertEqual(obs['category'],'infrastructure_error');self.assertNotIn('private_internal_detail',json.dumps(obs))

if __name__=='__main__':unittest.main()
