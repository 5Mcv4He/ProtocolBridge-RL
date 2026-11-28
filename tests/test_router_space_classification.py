import copy,unittest
from task_families.router_space import classify

class EngineeringSpace(unittest.TestCase):
    def request(self):return {'contract':{'task_id':'x2p_router_classa_v1','windows':[[4096,8192],[12288,4096],[1073741824,12288]],'purpose':'Adjacent target windows and high target'},'upstream':{'protocol':'AXI4-Lite','role':'slave','data_bits':32,'address_bits':32,'max_beats':1},'downstream':{'protocol':'APB4','role':'master','data_bits':32,'address_bits':32,'max_beats':1},'targets':3,'unretired_capacity':1,'delivery':'rtl_implementation'}
    def test_supported_is_not_admitted(self):
        r=classify(self.request());self.assertTrue(r['can_generate']);self.assertFalse(r['admitted'])
    def test_protocol_contradiction_is_not_missing_resource(self):
        r=self.request();r['upstream']['max_beats']=4
        self.assertEqual(classify(r)['status'],'contradictory_protocol_contract')
        r['upstream']['protocol']='AXI4'
        self.assertEqual(classify(r)['status'],'requires_contract_and_verification_resource')
    def test_independent_new_obligations(self):
        changes=[('unretired_capacity',2,'requires_composition_verification'),('targets',4,'requires_composition_verification'),('delivery','checker','requires_artifact_and_reward_profile')]
        for field,value,status in changes:
            r=self.request();r[field]=value;self.assertEqual(classify(r)['status'],status)
        r=self.request();r['upstream']['data_bits']=64;self.assertEqual(classify(r)['status'],'requires_width_oracle')
    def test_role_reversal_not_inherited(self):
        r=self.request();r['upstream']['role']='master';self.assertEqual(classify(r)['status'],'unqualified_endpoint_roles')

if __name__=='__main__':unittest.main()
