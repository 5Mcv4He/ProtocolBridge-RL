import unittest
from verifier.independent_formal.campaign import interpret,source_policy

GOOD="""PB_REFERENCE_READ=1
PB_REFERENCE_TOP=1
PB_CANDIDATE_READ=1
PB_CANDIDATE_TOP=1
PB_REFERENCE_EQ=1
PB_REFERENCE_DONE=1
No 'black boxes' matched current 'reference and implementation designs'
0(0) Unmatched reference(implementation) compare points
0(0) Unmatched reference(implementation) primary inputs, black-box outputs
16 Passing compare points
Verification SUCCEEDED
No unverified compare points.
No aborted compare points.
No failing compare points.
"""
class IndependentFormal(unittest.TestCase):
 def test_incomplete_or_ambiguous_never_passes(self):
  self.assertEqual(interpret(GOOD,0)['reward'],1)
  for old,new in [('16 Passing','0 Passing'),('0(0) Unmatched','1(0) Unmatched'),('No aborted compare points.',''),('No unverified compare points.',''),('PB_REFERENCE_DONE=1',''),('PB_REFERENCE_EQ=1','PB_REFERENCE_EQ=1\nPB_REFERENCE_EQ=0'),("No 'black boxes' matched current 'reference and implementation designs'",'one black box')]:
   self.assertIsNone(interpret(GOOD.replace(old,new),0)['reward'])
  self.assertIsNone(interpret(GOOD,124)['reward'])
  self.assertIsNone(interpret(GOOD,1)['reward'])
 def test_sources_cannot_insert_tcl_or_external_behavior(self):
  for source in ('', 'module accumulator; initial $system("x"); endmodule','`include "x"','module accumulator; assert (1); endmodule'):
   self.assertIsNotNone(source_policy(source))
  self.assertIsNone(source_policy('module accumulator(input clk); endmodule'))
