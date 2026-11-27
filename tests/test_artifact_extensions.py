import json,tempfile,unittest
from pathlib import Path
from environment.artifact_task.session_v2 import Session,sha
from verifier.stimulus.campaign import parse
from verifier.uart_tx.campaign import interpret
class ArtifactExtensions(unittest.TestCase):
 def test_stimulus_limits_and_executable_input_rejection(self):
  self.assertEqual(len(parse('{"transactions":[[1,256,1,15,0,0,0,0,0]]}')),1)
  for value in ({'transactions':[]},{'transactions':[[True,0,0,0,0,0,0,0,0]]},{'transactions':[[0,1,0,0,0,0,0,0,0]]},{'transactions':[[0,0,0,1,0,0,0,0,0]]},{'transactions':[[1,0,0,0,17,0,0,0,0]]},{'transactions':[[1,0,0,0,0,0,0,0,0]]*33},{'transactions':[],'code':'$fatal'}):
   with self.assertRaises(ValueError):parse(json.dumps(value))
 def test_uart_requires_activity_and_clean_completion(self):
  clean='UVM_WARNING : 0\nUVM_ERROR : 0\nUVM_FATAL : 0\n'
  self.assertIsNone(interpret(clean,0,0)['reward'])
  done='PB_UART_COMPLETE frames=256 cycle_checks=40960\n'
  self.assertEqual(interpret(clean+done,0,0)['reward'],1)
  self.assertIsNone(interpret(clean+done,124,0)['reward'])
  self.assertIsNone(interpret(clean+done,0,1)['reward'])
  self.assertIsNone(interpret(clean.replace('WARNING : 0','WARNING : 1')+done,0,0)['reward'])
 def test_current_session_enforces_versions_budgets_and_stop(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);(p/'spec.md').write_text('spec');(p/'stimulus.json').write_text('{}');calls=[]
   def grade(source,out,phase):
    calls.append((sha(source),phase));return {'reward':0,'category':'insufficient_detection','source_sha256':sha(source),'private':'hidden'}
   s=Session({'task_id':'x','deliverable':'stimulus.json'},p,p/'session',grade,max_actions=9,max_tests=2)
   for f in ('spec.md','stimulus.json'):s.handle({'tool':'read','file':f})
   a=s.handle({'tool':'test'});s.handle({'tool':'edit','content':'{"transactions":[]}'});b=s.handle({'tool':'test'})
   self.assertNotEqual(a['source_sha256'],b['source_sha256']);self.assertNotIn('private',b)
   self.assertEqual(s.handle({'tool':'test'})['reason'],'test_budget_exhausted');self.assertEqual(len(calls),2)
   s.handle({'tool':'submit'});self.assertEqual(len(calls),2)
   self.assertEqual(s.handle({'tool':'edit','content':'x'})['reason'],'episode_closed')
   with self.assertRaises(ValueError):s.finalize(False)
   self.assertEqual(s.finalize(True)['reward'],0)
