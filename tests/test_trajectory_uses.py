import copy,unittest
from research.trajectory_uses import analyze
class TrajectoryUses(unittest.TestCase):
    def row(self):
        return {'episode_id':'e','task_id':'task','final_submission':{'sha256':'b'},'outcome':{'reward':1,'valid_submission':True},'tool_events':[
          {'action_index':1,'executed':True,'action':{'tool':'edit','content_sha256':'a'},'observation':{'status':'EDITED'}},
          {'action_index':2,'executed':True,'action':{'tool':'test'},'observation':{'status':'FAIL','source_sha256':'a'},'observation_delivered':True},
          {'action_index':3,'executed':True,'action':{'tool':'edit','content_sha256':'b'},'observation':{'status':'EDITED'}},
          {'action_index':4,'executed':True,'action':{'tool':'test'},'observation':{'status':'PASS','source_sha256':'b'},'observation_delivered':True}]}
    def test_repair_requires_received_failure_and_changed_tested_source(self):
        row=self.row();self.assertIn('multi_step_repair_demonstration_review',analyze(row,'m')['potential_uses'])
        row['tool_events'][1]['observation_delivered']=False
        self.assertNotIn('multi_step_repair_demonstration_review',analyze(row,'m')['potential_uses'])
    def test_heldout_and_offline_do_not_select(self):
        a=self.row();b=copy.deepcopy(a);b.update(heldout={'reward':0},evaluation={'reward':0},posthoc={'reward':0})
        self.assertEqual(analyze(a,'m'),analyze(b,'m'))
    def test_old_pass_does_not_validate_new_source(self):
        row=self.row();row['final_submission']['sha256']='c'
        result=analyze(row,'m');self.assertEqual(result['final_public_status'],'not_observed')
        self.assertNotIn('multi_step_repair_demonstration_review',result['potential_uses'])
    def test_supersession_limits_use_without_rewriting_reward(self):
        result=analyze(self.row(),'m',True)
        self.assertEqual(result['reward'],1)
        self.assertNotIn('implementation_demonstration_review',result['potential_uses'])
    def test_null_is_not_zero(self):
        row=self.row();row['outcome']['reward']=None
        self.assertIsNone(analyze(row,'m')['reward'])
    def test_same_source_is_not_repair(self):
        row=self.row()
        row['tool_events'][2]['action']['content_sha256']='a';row['tool_events'][3]['observation']['source_sha256']='a'
        self.assertEqual(analyze(row,'m')['repair_evidence'],[])
    def test_hash_mismatch_quarantines_demonstration(self):
        row=self.row();row['tool_events'][3]['observation']['source_sha256']='other'
        result=analyze(row,'m');self.assertTrue(result['binding_issues'])
        self.assertNotIn('implementation_demonstration_review',result['potential_uses'])
