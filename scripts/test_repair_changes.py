import sys,unittest,tempfile,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from repair_changes import tokens,review,sha_bytes
class TokenChanges(unittest.TestCase):
 def test_comments_and_layout(self):
  self.assertEqual(tokens('x <= y; // hi\n'),tokens('/* hi */ x<=y;'))
 def test_logic_changes(self):
  self.assertNotEqual(tokens('count<=count-1;'),tokens('count<=count+1;'))
 def test_atomic_operators_and_names(self):
  self.assertNotEqual(tokens('a<=b;'),tokens('a< =b;'))
  self.assertNotEqual(tokens('ab'),tokens('a b'))
 def test_strings_not_comments(self):
  self.assertNotEqual(tokens('"// a"'),tokens('"// b"'))
class RepairEvidence(unittest.TestCase):
 def setup_cohort(self,root):
  start='module bridge; endmodule\n';(root/'starting.sv').write_text(start)
  name='r01-test_verdict';d=root/name;d.mkdir();(d/'submission').mkdir();(d/'submission/bridge.sv').write_text(start)
  (root/'experiment.json').write_text(json.dumps({'starting_rtl_sha256':sha_bytes(start.encode()),'schedule':[{'id':name,'policy':'test_verdict'}]}))
  (d/'metrics.json').write_text(json.dumps({'submitted':True,'terminal':{'reward':None,'category':'infrastructure_error'}}))
  (d/'trace.json').write_text(json.dumps([{'executed':True,'action':{'tool':'test'},'action_index':1,'observation':{'status':'FAIL','remaining_test_calls':1},'observation_delivered':True}]))
  return d
 def test_infrastructure_preserves_submission_and_exposure(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);self.setup_cohort(root);r=review(root,root/'review');row=r['trials'][0]
   self.assertIsNone(row['reward']);self.assertTrue(row['initial_failed_feedback_verified']);self.assertTrue(row['final_tokens_equal_start'])
 def test_submitted_code_must_match_observed_candidate(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);d=self.setup_cohort(root);(d/'submission/bridge.sv').write_text('module changed; endmodule')
   with self.assertRaisesRegex(ValueError,'source mismatch'):review(root,root/'review')
 def test_missing_trial_not_dropped(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);d=self.setup_cohort(root);(d/'metrics.json').unlink()
   with self.assertRaisesRegex(ValueError,'Complete repair cohort'):review(root,root/'review')
if __name__=='__main__':unittest.main()
