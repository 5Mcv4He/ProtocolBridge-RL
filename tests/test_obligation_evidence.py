import copy
import unittest
from scripts.obligation_evidence import link

class ObligationEvidence(unittest.TestCase):
    def test_rejects_declared_but_unexecuted_or_undetected_behavior(self):
        obligation=[{'id':'reset_target','stimulus':['reset_2'],'coverage':['target2_reset'],'controls':['bad_reset']}]
        ref={'reference':{'reward':1,'verification_complete':True,'cases':[{'name':'reset_2','reward':1,'coverage_bins':['target2_reset']}]}}
        negatives={'bad_reset':{'reward':0,'category':'protocol_timing_error','failed_case':'reset_2'}}
        self.assertEqual(link(obligation,ref,negatives)[0]['negative_evidence']['bad_reset']['reward'],0)
        for change in ('coverage','case','incomplete','null','compile'):
            r=copy.deepcopy(ref);n=copy.deepcopy(negatives)
            if change=='coverage':r['reference']['cases'][0]['coverage_bins']=[]
            elif change=='case':r['reference']['cases'][0]['name']='another_case'
            elif change=='incomplete':r['reference']['verification_complete']=False
            elif change=='null':n['bad_reset']['reward']=None
            else:n['bad_reset']['category']='compile_error'
            with self.assertRaises(ValueError):link(obligation,r,n)
