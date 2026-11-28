import json,unittest
import test_controller as base
from environment.native_tools.controller_v2 import Controller,digest
class NativeV2(base.NativeGate):
    def setUp(self):
        super().setUp();self.c=Controller(self.s,max_requests=2)
    def call(self,name,args=None):
        self.serial+=1
        return self.c.dispatch({'kind':'tool_request','call_id':str(self.serial),'name':name,'arguments':json.dumps(args if args is not None else {})})
    def test_replay_is_transport_failure(self):
        packet={'kind':'tool_request','call_id':'fixed','name':'test','arguments':'{}'}
        self.c.dispatch(packet)
        with self.assertRaises(ValueError):self.c.dispatch(packet)
        self.assertEqual(len(self.grades),1)
    def request(self,index,prior=[]):
        return self.c.dispatch({'kind':'model_request','call_id':'request-'+str(index),'request_index':index,'prior_tool_results':prior})
    def test_raw_arguments_not_repaired(self):
        for raw in ('','{"file":"spec.md","file":"candidate.sv"}','{"x":NaN}','[]','{} {}'):
            self.serial+=1
            reply=self.c.dispatch({'kind':'tool_request','call_id':str(self.serial),'name':'read','arguments':raw})
            self.assertEqual(reply['observation']['status'],'REJECTED')
            self.assertEqual(self.c.calls[-1]['raw_arguments'],raw)
    def test_request_limit_precedes_provider(self):
        self.assertFalse(self.request(1)['stop']);self.assertFalse(self.request(2)['stop'])
        self.assertTrue(self.request(3)['stop'])
        self.assertEqual(sum(r['allowed'] for r in self.c.requests),2)
    def test_receipt_requires_matching_result_and_response(self):
        self.request(1);self.call('test');self.c.returned('1')
        self.c.response_received({'type':'assistant/message','seq':10,'data':{'turn':1,'step':1}})
        self.assertFalse(self.s.trace[0]['observation_delivered'])
        self.request(2,[{'call_id':'1','text_sha256':digest(self.c.calls[0]['observation'])}])
        self.assertFalse(self.s.trace[0]['observation_delivered'])
        self.c.response_received({'type':'assistant/message','seq':20,'data':{'turn':1,'step':2}})
        self.assertTrue(self.s.trace[0]['observation_delivered'])
    def test_forged_observation_rejected(self):
        self.call('test');self.c.returned('1')
        with self.assertRaises(ValueError):self.request(1,[{'call_id':'1','text_sha256':'0'*64}])
if __name__=='__main__':unittest.main()
