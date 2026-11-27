import json,tempfile,unittest
from pathlib import Path
from environment.artifact_task.session_v5 import Session,sha,prompt
from environment.artifact_task.session_v4 import prompt as previous_prompt
class ActionDiagnostics(unittest.TestCase):
 def test_extra_key_rejected_without_edit_and_corrected_action_is_separate(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);w=p/'work';w.mkdir();(w/'spec.md').write_text('spec');(w/'design.sv').write_text('initial');calls=[]
   s=Session({'task_id':'fixture','deliverable':'design.sv'},w,p/'session',lambda *args:calls.append(args),20,4)
   for f in ('spec.md','design.sv'):s.handle({'tool':'read','file':f})
   o=s.handle({'tool':'edit','file':'PRIVATE_CANARY','content':'replacement'})
   self.assertEqual(o['reason'],'invalid_action_format');self.assertIn('NO file key',o['instruction']);self.assertNotIn('PRIVATE_CANARY',json.dumps(o))
   self.assertEqual((w/'design.sv').read_text(),'initial');self.assertEqual(s.edits,0);self.assertFalse(calls)
   self.assertEqual(json.loads((s.out/'trace.json').read_text())[-1]['observation'],o)
   self.assertEqual(s.handle({'tool':'edit','content':'replacement'})['status'],'EDITED');self.assertEqual(s.edits,1)
   self.assertEqual(s.actions,4);self.assertEqual(json.loads((s.out/'session.json').read_text())['version'],'engineering-artifact-session-v5')
 def test_initial_prompt_and_atomic_parser_unchanged(self):
  self.assertEqual(prompt('design.sv',20,4),previous_prompt('design.sv',20,4))
  from environment.policy import parse_action
  with self.assertRaises(ValueError):parse_action('{"tool":"edit","content":"x"}\n{"tool":"test"}')
if __name__=='__main__':unittest.main()
