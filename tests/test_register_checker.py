import unittest
from verifier.register_checker.model import annotate,anchors,corpus
from verifier.register_checker.campaign import source_policy,interpret
from task_families.register_checker_v1.generate import reference
class RegisterChecker(unittest.TestCase):
 def test_literal_semantic_anchors(self):self.assertEqual(anchors(),{'w1c_literal_cycles':12,'rw_literal_cycles':11})
 def test_all_phases_require_interactions(self):
  for mode in ('rw','w1c'):
   for phase in ('public','terminal','evaluation'):
    rows,c=corpus(mode,phase);self.assertEqual(c['bad_address_bit_pairs'],128);self.assertEqual(c['bad_read_addresses'],16);self.assertTrue(all(c.values()));self.assertEqual(len(rows),4648)
 def test_wrong_read_does_not_repair_prediction_or_clear_error(self):
  r,_=annotate([[0,0,0,0,0,0],[1,1,1,2,7,0],[1,1,0,2,0,3],[1,1,0,2,0,7],[0,1,1,2,9,0],[1,1,0,2,0,0]],'rw');self.assertEqual([x[-1] for x in r],[0,0,1,1,0,0])
 def test_legal_modes_have_distinct_obligations(self):
  e=[[0,0,0,0,0,0],[1,1,1,1,1,0],[1,1,1,1,2,0],[1,1,0,1,0,252]]
  self.assertEqual(annotate(e,'w1c')[0][-1][-1],0);self.assertEqual(annotate(e,'rw')[0][-1][-1],1)
 def test_candidate_cannot_report_verdict(self):
  for m in ('rw','w1c'):
   self.assertIsNone(source_policy(reference(m)));self.assertIsNone(source_policy(reference(m,True)))
  self.assertIsNotNone(source_policy(reference('rw').replace('endmodule','initial $finish;endmodule')))
 def test_missing_partial_duplicate_or_tool_failure_is_not_pass(self):
  for log,rc in [('',0),('PB_CHECKER_COMPLETE rows=1\n',0),('PB_CHECKER_COMPLETE rows=2\n'*2,0),('PB_CHECKER_COMPLETE rows=2\n',1),('PB_CHECKER_COMPLETE rows=2\n',124)]:self.assertIsNone(interpret(log,rc,2)['reward'])
 def test_bad_output_is_functional_error(self):self.assertEqual(interpret('PB_CHECKER_MISMATCH row=1 expected=1 observed=0\n',0,2)['reward'],0)
if __name__=='__main__':unittest.main()
