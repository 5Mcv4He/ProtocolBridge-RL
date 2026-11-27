import tempfile,unittest
from pathlib import Path
from environment.artifact_task.feedback_v2 import ExplicitRejectionSession
from environment.policy import parse_action
class RejectionFeedback(unittest.TestCase):
 def test_atomic_rejection_with_instruction_and_no_execution(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);(p/'spec.md').write_text('spec');(p/'x.json').write_text('{}')
   def forbidden(*args):raise AssertionError('No checker may run')
   s=ExplicitRejectionSession({'task_id':'x','deliverable':'x.json'},p,p/'session',forbidden)
   with self.assertRaises(ValueError):parse_action('{"tool":"test"}\n{"tool":"submit"}')
   o=s.handle({'tool':'invalid'})
   self.assertIn('No action from this reply was executed',o['instruction'])
   self.assertFalse(s.trace[-1]['executed']);self.assertEqual(s.tests,0);self.assertEqual(s.actions,1)
   self.assertEqual(s.trace[-1]['observation'],o)
