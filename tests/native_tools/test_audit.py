import unittest
from environment.native_tools.audit import audit
from environment.native_tools.controller_v2 import digest
class Audit(unittest.TestCase):
    def records(self):
        observation={'status':'FAIL'}
        calls=[{'request':{'call_id':'x','name':'test'},'raw_arguments':'{}','observation':observation,'observation_text_sha256':digest(observation),'executed':True,'action_index':1,'model_receipt_confirmed':False}]
        events=[{'kind':'notification','notification':{'method':'session.event','payload':{'event':{'type':'assistant/message','data':{'message':{'content':[{'type':'tool-call','id':'x','name':'test','arguments':'{}'}]}}}}}},
        {'kind':'notification','notification':{'method':'session.event','payload':{'event':{'type':'tool/result','data':{'message':{'toolCallId':'x','content':[{'type':'text','text':'{"status":"FAIL"}'}]}}}}}}]
        return events,calls,[{'response_received':True}]
    def test_exact_observation(self):
        self.assertTrue(audit(*self.records(),False)['accepted'])
    def test_sdk_leak_rejected(self):
        e,c,r=self.records();e[-1]['notification']['payload']['event']['data']['message']['content'][0]['text']='private extra'
        with self.assertRaises(ValueError):audit(e,c,r,False)
    def test_unaccounted_call_rejected(self):
        e,c,r=self.records()
        with self.assertRaises(ValueError):audit(e,[],r,False)
