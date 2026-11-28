import copy
import unittest
from research.generated_trajectory_uses import review


class Uses(unittest.TestCase):
    def row(self):
        return dict(schema='pb-tool-trajectory-v12',episode_id='e',task_id='t',
            outcome=dict(submitted=True,valid_submission=True,reward=0),final_submission=dict(sha256='b'),
            native_calls=[dict(action_index=2,model_receipt_confirmed=True)],
            tool_events=[dict(action_index=1,executed=True,action=dict(tool='edit'),observation=dict(source_sha256='a')),
              dict(action_index=2,executed=True,action=dict(tool='test'),observation=dict(status='FAIL',category='transaction_functional_error',source_sha256='a'),observation_delivered=True),
              dict(action_index=3,executed=True,action=dict(tool='edit'),observation=dict(source_sha256='b'))])

    def test_untested_final_not_promoted_to_repair(self):
        r=review(self.row(),'manifest')
        self.assertFalse(r['final_candidate_publicly_measured'])
        self.assertEqual(r['repair_evidence'],[])
        self.assertNotIn('implementation_demonstration_review',r['potential_uses'])

    def test_heldout_does_not_change_selection(self):
        a=self.row();b=copy.deepcopy(a);b['evaluation']={'reward':1};b['offline']={'best_candidate':'a'}
        self.assertEqual(review(a,'m'),review(b,'m'))

    def test_receipt_and_identity_required(self):
        r=self.row();r['native_calls'][0]['model_receipt_confirmed']=False
        with self.assertRaises(ValueError):review(r,'m')
        r=self.row();r['tool_events'][1]['observation']['source_sha256']='other'
        with self.assertRaises(ValueError):review(r,'m')


if __name__=='__main__':unittest.main()
