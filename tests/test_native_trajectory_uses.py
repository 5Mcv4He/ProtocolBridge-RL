import copy,unittest
from research.native_trajectory_uses import review
class Uses(unittest.TestCase):
 def row(self):
  return {'schema':'pb-tool-trajectory-v9','episode_id':'e','task_id':'t','outcome':{'submitted':True,'reward':0},'final_submission':{'sha256':'b'},'native_calls':[{'action_index':2,'model_receipt_confirmed':True},{'action_index':4,'model_receipt_confirmed':True}],
   'tool_events':[{'action_index':1,'executed':True,'action':{'tool':'edit'},'observation':{'source_sha256':'a'}},{'action_index':2,'executed':True,'action':{'tool':'test'},'observation':{'status':'FAIL','category':'synthesis_error','source_sha256':'a','measurement':{'functional_checks_passed':True,'mapped_cell_count':23,'limit':22}},'observation_delivered':True},{'action_index':3,'executed':True,'action':{'tool':'edit'},'observation':{'source_sha256':'b'}},{'action_index':4,'executed':True,'action':{'tool':'test'},'observation':{'status':'FAIL','category':'transaction_mismatch','source_sha256':'b'},'observation_delivered':True}]}
 def test_functional_regression_not_resource_success(self):
  r=review(self.row(),'m');self.assertEqual(len(r['functional_regression_evidence']),1);self.assertNotIn('implementation_demonstration_review',r['potential_uses'])
 def test_no_functional_inference_from_generic_fail(self):
  r=self.row();r['tool_events'][1]['observation'].pop('measurement');self.assertEqual(review(r,'m')['functional_regression_evidence'],[])
 def test_no_unmeasured_regression(self):
  r=self.row();r['tool_events'].pop();self.assertEqual(review(r,'m')['functional_regression_evidence'],[])
 def test_receipt_must_match(self):
  r=self.row();r['native_calls'][0]['model_receipt_confirmed']=False
  with self.assertRaises(ValueError):review(r,'m')
 def test_heldout_has_no_effect(self):
  a=self.row();b=copy.deepcopy(a);b['evaluation']={'reward':1};b['offline']={'best_candidate':'c'};self.assertEqual(review(a,'m'),review(b,'m'))
if __name__=='__main__':unittest.main()
