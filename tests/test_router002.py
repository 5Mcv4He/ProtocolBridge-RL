"""Task002 contract checks; none replace licensed simulation."""
import unittest
from pathlib import Path
from verifier.task002.scenarios import suite,target
from verifier.task002.campaign import interpret,source_policy

class RouterContract(unittest.TestCase):
 def test_decode_boundaries(self):
  for a,t in [(0x1000,0),(0x1ffc,0),(0x2000,-1),(0x8000,1),(0x9000,1),(0x9ffc,1),(0xa000,-1),(0x40000000,2),(0x40000ffc,2),(0x40001000,-1),(0x80001000,-1),(0xfffffffc,-1)]:self.assertEqual(target(a),t)
 def test_all_target_cross(self):
  rows=[r for c in suite() if c['name'].startswith('strobe_cross') for r in c['rows'] if r[0]]
  seen={(target(r[1]),r[3],2 if r[4] else 1 if r[5] else 0,r[8],0 if not r[6] else 1 if r[6]<=8 else 2,int(r[7]>0)) for r in rows}
  self.assertEqual(len(seen),1728)
 def test_reset_target_stage_cross(self):
  c=next(c for c in suite() if c['name']=='router_reset')
  self.assertEqual({(target(r[1]),r[9]) for r in c['rows'] if r[9]}, {(t,s) for t in range(3) for s in range(1,9)}|{(-1,s) for s in (1,2,7,8)})
 def test_stimulus_repeatable_and_aligned(self):
  self.assertEqual(suite(seed=1),suite(seed=1));self.assertNotEqual(suite(seed=1),suite(seed=2))
  self.assertEqual(len(suite(True)),21);self.assertEqual(len(suite()),26)
  for c in suite():
   for r in c['rows']:self.assertEqual(r[1]%4,0);self.assertEqual(len(r),11)
 def test_initial_and_references_allowed(self):
  for p in [Path('tasks/axil_to_apb4_router_002/workspace/bridge.sv')]+list(Path('fixtures/task002').glob('reference*.sv')):self.assertIsNone(source_policy(p))
 def test_miss_requires_zero_apb_accounting(self):
  c={'rows':[[0,0,0,0,0,0,0,0,0,0,0]],'sequence':'address_data_sequence','ready_mode':'early'}
  log='PB2_SEQUENCE address_data_sequence\nPB2_DONE\nPB2_RESULT planned=1 axi=1 apb=0 checked=1 aborted=0 aborted_apb=0 errors=0\nPB2_ROUTE mapped=0 unmapped=1 target0=0 target1=0 target2=0\nPB2_LATENCY accept_to_setup=0 completion_to_valid=1 waits=0 stalls=0\nUVM_ERROR : 0\nUVM_FATAL : 0\n'
  self.assertEqual(interpret(log,0,c)['reward'],1)
  self.assertEqual(interpret(log.replace('apb=0','apb=1'),0,c)['reward'],0)
  self.assertIsNone(interpret(log.replace('PB2_ROUTE','missing'),0,c)['reward'])
 def test_incomplete_and_infrastructure_not_functional(self):
  c=suite(True)[0]
  for log,rc in [('',143),('PB_INFRA\nPB2_TIMEOUT',0),('PB2_DONE',0)]:self.assertIsNone(interpret(log,rc,c)['reward'])
 def test_confirmed_failures_classified(self):
  c=suite(True)[0]
  for log,category in [('UVM_ERROR [PB_TIMING] violation','protocol_timing_error'),('UVM_ERROR [PB_FUNCTION] mismatch','transaction_functional_error'),('PB2_TIMEOUT','test_timeout')]:
   r=interpret(log,0,c);self.assertEqual(r['reward'],0);self.assertEqual(r['category'],category)
if __name__=='__main__':unittest.main()
