import copy
import unittest
from scripts.package_behavior import regressions


class PublicRegression(unittest.TestCase):
    def records(self):
        return [dict(action_index=i,source_sha256=str(i),inputs={'case':{'rows':[[1,2,3]]}},
                     cases=[dict(name='case',reward=1 if i==1 else 0,category='pass' if i==1 else 'protocol_timing_error')]) for i in (1,2)]

    def test_requires_same_actual_inputs_and_distinct_source(self):
        t=self.records();self.assertEqual(len(regressions(t)),1)
        changed=copy.deepcopy(t);changed[1]['inputs']['case']['rows'][0][0]=7
        self.assertEqual(regressions(changed),[])
        changed=copy.deepcopy(t);changed[1]['source_sha256']='1'
        self.assertEqual(regressions(changed),[])

    def test_missing_and_infrastructure_outcomes_are_not_regressions(self):
        for reward,category in [(None,'infrastructure_error'),(0,'compile_error')]:
            t=self.records();t[1]['cases'][0].update(reward=reward,category=category)
            self.assertEqual(regressions(t),[])
        t=self.records();t[0]['cases']=[];self.assertEqual(regressions(t),[])
