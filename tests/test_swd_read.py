import unittest
from pathlib import Path
from verifier.swd_read.corpus import corpus
from verifier.swd_read.campaign import interpret,source_policy,candidate_compile_error
class SwdRead(unittest.TestCase):
 def test_inputs_cover_each_bit_and_capture(self):
  for phase in ('public','terminal','evaluation'):
   rows,c=corpus(phase);self.assertEqual(len(rows),48)
   self.assertEqual(sum(r[0]!=0 for r in rows),c['line_resets']);self.assertEqual(sum(r[0]==2 for r in rows),c['physical_resets'])
   self.assertTrue(all(v!=changed for _,v,changed in rows));self.assertTrue(all(1<<b in [r[1] for r in rows] for b in range(32)))
 def test_no_implicit_pass_from_uvm_or_partial_counts(self):
  c=corpus('public')[1];good='PB_SWD_COMPLETE pins=48 responses=48 lines=6 resets=3\nUVM_WARNING : 0\nUVM_ERROR : 0\nUVM_FATAL : 0\n'
  self.assertEqual(interpret(good,0,c)['reward'],1)
  for log,rc in [(good.replace('pins=48','pins=47'),0),(good+good,0),(good,1),(good,124),(good.replace('UVM_ERROR : 0','UVM_ERROR : 1'),0),(good+'PB_SWD_INFRA input\n',0)]:self.assertIsNone(interpret(log,rc,c)['reward'])
 def test_independent_mismatch_vs_environment(self):
  c=corpus('public')[1]
  self.assertEqual(interpret('PB_SWD_MISMATCH data read payload\n',0,c)['category'],'transaction_mismatch')
  self.assertEqual(interpret('PB_SWD_MISMATCH timing ACK\n',0,c)['reward'],0)
  self.assertIsNone(interpret('PB_SWD_INFRA request\n',0,c)['reward'])
 def test_compile_location_attribution(self):
  self.assertTrue(candidate_compile_error('Error-[SE] Syntax error\n  "candidate.sv", 7: token is ;\n'))
  self.assertTrue(candidate_compile_error('Error-[SE] Syntax error\ncandidate.sv, 7: token is ;\n'))
  self.assertFalse(candidate_compile_error("Parsing design file candidate.sv \nError-[SE] Syntax error\n  \"tb.sv\", 8: token is ;\n"))
 def test_source_boundary(self):
  ref=Path('tasks/swd_read_v1/reference.sv').read_text();self.assertIsNone(source_policy(ref))
  for s in ['',ref.replace('endmodule','initial $finish;endmodule'),ref.replace('read_value','other'),ref+'module extra();endmodule']:
   self.assertIsNotNone(source_policy(s))
if __name__=='__main__':unittest.main()
