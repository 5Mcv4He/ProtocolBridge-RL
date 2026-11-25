"""Task003 Python plan/classifier tests; licensed driver and RTL still need simulation."""
import unittest
from pathlib import Path
from verifier.task003.scenarios import suite,REQUIRED_BINS
from verifier.task003.campaign import interpret,source_policy
class QueueContract(unittest.TestCase):
 def test_plans_reproducible_and_legal(self):
  self.assertEqual(suite(seed=1),suite(seed=1));self.assertNotEqual(suite(seed=1),suite(seed=2))
  self.assertEqual(len(suite(True)),19);self.assertEqual(len(suite()),21)
  for c in suite():
   for r in c['rows']+c['recovery']:
    self.assertEqual(len(r),10);self.assertEqual(r[1]%4,0);self.assertIn(r[0],(0,1));self.assertIn(r[8],(0,1));self.assertTrue(0<=r[3]<16);self.assertFalse(r[4] and r[5])
 def test_reset_stages_and_recovery(self):
  c=[x for x in suite() if x['reset_stage']]
  self.assertEqual({x['reset_stage'] for x in c},set(range(1,9)))
  for x in c:self.assertEqual(len(x['rows']),4);self.assertEqual(len(x['recovery']),8)
  for x in c:
   if x['reset_stage']<5:self.assertTrue(all(r[9]==0 for r in x['rows']))
 def test_synthesis_submission_subset(self):
  for p in Path('fixtures/task003').glob('*.sv'):self.assertIsNone(source_policy(p),p.name)
 def test_complete_case_and_credit_ledger(self):
  case={'rows':[[1,0,0,15,0,0,0,0,0,0]],'recovery':[],'reset_stage':0,'sequence':'queue_request_sequence'}
  log='PBQ_SEQUENCE queue_request_sequence\nPBQ_DONE\nPBQ_RESULT planned=1 axi=1 apb=1 checked=1 aborted=0 aborted_apb=0 errors=0\nPBQ_CREDITS aw=1 w=1 ar=0 retired_w=1 retired_r=0 canceled_aw=0 canceled_w=0 canceled_ar=0 resets=0 grants=1\nUVM_ERROR : 0\nUVM_FATAL : 0\n'
  self.assertEqual(interpret(log,0,case)['reward'],1)
  self.assertEqual(interpret(log.replace('aw=1','aw=2'),0,case)['reward'],0)
  self.assertIsNone(interpret(log.replace('PBQ_CREDITS','missing'),0,case)['reward'])
 def test_unknown_watchdog_not_mislabeled_rtl(self):
  c=suite(True)[0]
  self.assertIsNone(interpret('PBQ_TIMEOUT',0,c)['reward'])
  self.assertEqual(interpret('UVM_ERROR [PB_TIMING] Registered FIFO grant/setup missing',0,c)['reward'],0)
  self.assertIsNone(interpret('PB_INFRA\nUVM_ERROR [PB_TIMING] failure',0,c)['reward'])
 def test_feedback_projection(self):
  from environment.task003 import project
  from environment.policy import load
  internal={'reward':0,'category':'transaction_functional_error','failed_case':'write_fifo','secret':'do not leak'}
  c=project(internal,load('test_verdict'),1);e=project(internal,load('test_diagnostic'),1)
  self.assertEqual(set(c),{'status','remaining_test_calls'})
  self.assertEqual(e['first_failed_case'],'write_fifo');self.assertNotIn('secret',str(e))
 def test_requirement_bin_count(self):self.assertEqual(len(REQUIRED_BINS),33)
if __name__=='__main__':unittest.main()
