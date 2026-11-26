import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from scripts.rollout_exchange_v3 import export
class ExchangeV3(unittest.TestCase):
 def fixture(self,root,extra=False):
  d=root/'trial';d.mkdir();(d/'submission').mkdir();(d/'submission/bridge.sv').write_text('module bridge; endmodule')
  m={'capabilities':'synthesis-tools-v1','schedule':[{'id':'trial'}],'task_id':'axil_to_apb4_queue_003','model':'model','protocol':'text-json-atomic-v2','study':'repair','source_commit':'abc','source_files':{},'toolchain':{}}
  (root/'experiment.json').write_text(json.dumps(m));(d/'initial-prompt.txt').write_text('prompt')
  metric={'submitted':True,'policy_sha256':'policy','private_reward_suite_sha256':'reward-hash','reserved_evaluation_suite_sha256':'heldout-hash','synth_calls':1}
  (d/'metrics.json').write_text(json.dumps(metric))
  observation={'status':'PASS','diagnostics':[],'functional_correctness_checked':False,'remaining_synth_calls':1}
  if extra:observation['private']='SECRET'
  (d/'trace.json').write_text(json.dumps([{'action_index':1,'action':{'tool':'synth_check'},'executed':True,'observation_delivered':True,'observation':observation}]))
  return {'rows':[{'trial':'trial','policy':'test_diagnostic','reward':0,'valid_submission':True,'terminal_category':'protocol_timing_error','held_out':1,'first_candidate_public':None}]}
 def test_feedback_and_evaluation_partition(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)/'raw';root.mkdir();a=self.fixture(root)
   with patch('scripts.rollout_exchange_v3.audit',return_value={'accepted':True}),patch('scripts.rollout_exchange_v3.report',return_value=a):r=export([root],Path(d)/'out')
   training=json.loads((Path(d)/'out/training/rollouts.jsonl').read_text());evaluation=json.loads((Path(d)/'out/evaluation/heldout.jsonl').read_text())
   self.assertEqual(r['records'],1);self.assertEqual(training['outcome']['reward'],0)
   self.assertNotIn('heldout-hash',json.dumps(training));self.assertEqual(evaluation['held_out_reward'],1)
   self.assertFalse(training['tool_events'][0]['observation']['functional_correctness_checked'])
 def test_unknown_observation_and_failed_audit_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)/'raw';root.mkdir();a=self.fixture(root,True)
   with patch('scripts.rollout_exchange_v3.audit',return_value={'accepted':False}):
    with self.assertRaises(ValueError):export([root],Path(d)/'out0')
   with patch('scripts.rollout_exchange_v3.audit',return_value={'accepted':True}),patch('scripts.rollout_exchange_v3.report',return_value=a):
    with self.assertRaises(ValueError):export([root],Path(d)/'out')
