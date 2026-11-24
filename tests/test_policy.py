import copy,json,tempfile,unittest
from pathlib import Path
from environment.policy import load,validate,prompt,policy_hash
from environment.feedback import project
from environment.policy_session import Session

class PolicyTests(unittest.TestCase):
    def setup_session(self,mode,result=None):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);p=Path(t.name);work=p/'work';work.mkdir()
        (work/'spec.md').write_text('SPEC');(work/'bridge.sv').write_text('module bridge; endmodule')
        calls=[]
        def grader(source,dest,**kw):
            calls.append(kw)
            return result or {'reward':0.0,'category':'protocol_timing_error','failed_case':'address_data',
                             'cases':[{'name':'address_data','timing_failures':['AXI acceptance exceeded 16 cycles']}],
                             'secret':'SENSITIVE_SENTINEL','log':'/private/SENSITIVE_SENTINEL'}
        s=Session(load(mode),work,p/'run',[{'private':'SENSITIVE_SENTINEL'}],grader)
        return s,calls
    def ready(self,s):
        for f in ('spec.md','bridge.sv'):s.handle({'tool':'read','file':f})
    def test_a_denied_before_any_grader_call_and_direct_submit(self):
        s,calls=self.setup_session('spec_only');self.ready(s)
        self.assertEqual(s.handle({'tool':'test'})['status'],'REJECTED');self.assertEqual(calls,[])
        self.assertEqual(s.handle({'tool':'submit'})['status'],'SUBMITTED');self.assertEqual(calls,[])
        s.finalize();self.assertEqual(calls,[{'reuse_build':None,'cases':[{'private':'SENSITIVE_SENTINEL'}]}])
    def test_c_exact_field_whitelist(self):
        s,calls=self.setup_session('test_verdict');r=s.handle({'tool':'test'})
        self.assertEqual(r,{'status':'FAIL','remaining_test_calls':1})
    def test_e_safe_specific_diagnostic(self):
        s,calls=self.setup_session('test_diagnostic');r=s.handle({'tool':'test'})
        self.assertEqual(r['first_failed_case'],'address_data');self.assertIn('16-cycle',r['diagnostic'])
        self.assertNotIn('SENSITIVE_SENTINEL',json.dumps(r))
    def test_third_test_does_not_execute(self):
        for mode in ('test_verdict','test_diagnostic'):
            s,calls=self.setup_session(mode)
            for _ in range(2):s.handle({'tool':'test'})
            self.assertEqual(s.handle({'tool':'test'})['reason'],'test_budget_exhausted')
            self.assertEqual(len(calls),2)
    def test_env_error_is_not_rtl_failure_and_counts_invocation(self):
        for mode in ('test_verdict','test_diagnostic'):
            s,calls=self.setup_session(mode,{'reward':None,'category':'infrastructure_error','reason':'SENSITIVE_SENTINEL'})
            r=s.handle({'tool':'test'});self.assertEqual(r['status'],'ENV_ERROR');self.assertEqual(s.tests,1)
            self.assertNotIn('SENSITIVE_SENTINEL',json.dumps(r))
    def test_sensitive_injection_in_all_free_text_fields(self):
        r={'reward':0,'category':'SENSITIVE_SENTINEL','failed_case':'SENSITIVE_SENTINEL','cases':[{'name':'SENSITIVE_SENTINEL','timing_failures':['SENSITIVE_SENTINEL']}], 'log':'SENSITIVE_SENTINEL','diagnostic':'SENSITIVE_SENTINEL'}
        for mode in ('test_verdict','test_diagnostic'):
            self.assertNotIn('SENSITIVE_SENTINEL',json.dumps(project(r,load(mode),0)))
        r.update(category='protocol_timing_error',failed_case='address_data',cases=[{'name':'address_data','timing_failures':['AXI acceptance exceeded 16 cycles SENSITIVE_SENTINEL']}])
        self.assertNotIn('SENSITIVE_SENTINEL',json.dumps(project(r,load('test_diagnostic'),0)))
    def test_private_files_and_tools_denied(self):
        for mode in ('spec_only','test_verdict','test_diagnostic'):
            s,calls=self.setup_session(mode)
            for path in ('../spec.md','policy.json','verifier/v3/vip.sv','fixtures/reference.sv','/private/reward.json'):
                self.assertEqual(s.handle({'tool':'read','file':path})['status'],'REJECTED')
            self.assertEqual(s.handle({'tool':'edit','file':'policy.json','content':'x'})['status'],'REJECTED')
            self.assertEqual(s.handle({'tool':'shell','command':'cat /private/reward.json'})['status'],'REJECTED')
            self.assertEqual(calls,[])
    def test_c_e_only_feedback_identity_diff_and_equal_prompt(self):
        c=load('test_verdict');e=load('test_diagnostic')
        self.assertEqual({k for k in c if c[k]!=e[k]},{'policy_id','feedback_level'})
        self.assertEqual(prompt(c),prompt(e));self.assertNotEqual(policy_hash(c),policy_hash(e))
    def test_invalid_policy_rejected_without_widening(self):
        for key,value in [('allowed_tools',['read','edit','test','submit','shell']),('readable_files',['*']),('max_agent_actions',True),('max_public_test_calls',3),('feedback_level','raw'),('final_reward_visibility','full')]:
            p=load('test_verdict');p[key]=value
            with self.assertRaises(ValueError):validate(p)
        p=load('spec_only');p['unknown']=True
        with self.assertRaises(ValueError):validate(p)
    def test_action_budget_and_after_submit_closed(self):
        s,calls=self.setup_session('spec_only')
        for _ in range(20):s.handle({'tool':'shell'})
        self.assertEqual(s.handle({'tool':'submit'})['reason'],'episode_closed');self.assertEqual(s.actions,20)
        s,calls=self.setup_session('spec_only');self.ready(s);s.handle({'tool':'submit'})
        self.assertEqual(s.handle({'tool':'edit','content':'module bridge; endmodule'})['reason'],'episode_closed')
    def test_terminal_rules_identical_in_all_modes(self):
        invocations=[]
        for mode in ('spec_only','test_verdict','test_diagnostic'):
            s,calls=self.setup_session(mode);self.ready(s);s.handle({'tool':'submit'});s.finalize();invocations.append(calls)
        self.assertEqual(invocations[0],invocations[1]);self.assertEqual(invocations[1],invocations[2])
    def test_projection_pass_requires_complete_verification(self):
        self.assertEqual(project({'reward':1,'category':'pass'},load('test_verdict'),1)['status'],'ENV_ERROR')
        self.assertEqual(project({'reward':1,'category':'pass','verification_complete':True},load('test_verdict'),1)['status'],'PASS')
    def test_verifier_exception_not_forwarded(self):
        s,calls=self.setup_session('test_diagnostic')
        def broken(*a,**kw):raise RuntimeError('SENSITIVE_SENTINEL')
        s.grader=broken;r=s.handle({'tool':'test'})
        self.assertEqual(r['status'],'ENV_ERROR');self.assertNotIn('SENSITIVE_SENTINEL',json.dumps(r))
    def test_trace_records_exact_projected_observation(self):
        s,calls=self.setup_session('test_verdict');r=s.handle({'tool':'test'})
        self.assertEqual(json.loads((s.out/'trace.json').read_text())[0]['observation'],r)

if __name__=='__main__':unittest.main()
