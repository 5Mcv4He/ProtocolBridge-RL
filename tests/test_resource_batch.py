import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from environment.artifact_task.batch_v2 import batch,usage
from environment.artifact_task.session_v4 import sha

class BatchTests(unittest.TestCase):
 def fixture(self,t):
  root=Path(t);plan=root/'plan.json';base=root/'runs';base.mkdir()
  p={'trials':[{'trial_id':'one','task_id':'fixture'},{'trial_id':'two','task_id':'fixture'}], 'resource_envelope':{'max_started_trials':2,'reported_token_stop':1000,'minimum_free_disk_bytes':100,'minimum_available_memory_bytes':100,'maximum_load_1m':2}}
  plan.write_text(json.dumps(p));return plan,base
 def test_resume_preserves_completed_and_stops_on_indeterminate(self):
  with tempfile.TemporaryDirectory() as t:
   plan,base=self.fixture(t);one=base/'one';one.mkdir();r={'trial_id':'one','plan_sha256':sha(plan),'terminal':{'reward':None,'category':'infrastructure_error'},'solver_stop_confirmed':False};(one/'result.json').write_text(json.dumps(r))
   before=(one/'result.json').read_bytes()
   with patch('environment.artifact_task.batch_v2.unchanged',return_value=True),patch('environment.artifact_task.batch_v2.run') as run:
    self.assertEqual(len(batch(plan,base,Path(t)/'private-config')),1);run.assert_not_called()
   self.assertEqual(before,(one/'result.json').read_bytes());self.assertFalse((base/'two').exists())
 def test_partial_episode_never_resampled(self):
  with tempfile.TemporaryDirectory() as t:
   plan,base=self.fixture(t);(base/'one').mkdir()
   with patch('environment.artifact_task.batch_v2.unchanged',return_value=True),patch('environment.artifact_task.batch_v2.run') as run:
    with self.assertRaises(RuntimeError):batch(plan,base,Path(t)/'private-config')
    run.assert_not_called()
 def test_busy_tools_stop_before_model(self):
  with tempfile.TemporaryDirectory() as t:
   plan,base=self.fixture(t)
   probe={'active_eda_processes':1,'free_disk_bytes':1000,'available_memory_bytes':1000,'load_1m':0}
   with patch('environment.artifact_task.batch_v2.unchanged',return_value=True),patch('environment.artifact_task.batch_v2.resource_probe',return_value=probe),patch('environment.artifact_task.batch_v2.run') as run:
    self.assertEqual(batch(plan,base,Path(t)/'private-config'),[]);run.assert_not_called()
 def test_usage_counts_failed_started_episodes(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'failed';p.mkdir();(p/'freeze.json').write_text('{}')
   (p/'harness-00.json').write_text(json.dumps({'response':{'events':[{'type':'assistant/message','data':{'usage':{'totalTokens':123}}}]}}))
   self.assertEqual(usage(t),{'started':1,'tokens':123})

if __name__=='__main__':unittest.main()
