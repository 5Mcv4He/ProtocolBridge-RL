import json,tempfile,unittest
from pathlib import Path
from environment.synthesis_projection import dc_observation,formal_result,measurement_result,validate_observation
from environment.synthesis_session import session_class
from environment.policy import load

class SynthesisTools(unittest.TestCase):
    def test_capacity_control_requires_confirmed_violation(self):
        from environment.synthesis_acceptance import capacity_control_rejected
        for category in ('protocol_timing_error','transaction_functional_error'):
            result={'reward':0,'category':category,'cases':[{'failures':['Request capacity exceeded']}]}
            self.assertTrue(capacity_control_rejected(result))
            self.assertFalse(capacity_control_rejected(dict(result,reward=None)))
            self.assertFalse(capacity_control_rejected(dict(result,category='infrastructure_error')))
            self.assertFalse(capacity_control_rejected(dict(result,cases=[])))

    def test_projection(self):
        log='PB_COMPILE=1\nPB_DC_DONE=1\nPB_LATCHES=1\nWarning: SECRET path (LINT-1)\n'
        value=dc_observation(log,0,True)
        self.assertEqual(value['status'],'PASS')
        self.assertEqual(value['diagnostics'][0]['code'],'LATCH_INFERRED')
        self.assertNotIn('SECRET',json.dumps(value))
        for text,rc,netlist in [(log,124,True),(log+'Error: unknown\n',0,True),(log,0,False),(log+'PB_DC_DONE=1\n',0,True)]:
            self.assertEqual(dc_observation(text,rc,netlist)['status'],'ENV_ERROR')
        self.assertEqual(dc_observation('Error: bridge.sv syntax\nPB_ANALYZE=0\n',0,False)['status'],'FAIL')
        self.assertEqual(dc_observation('Error: private.tcl\nPB_ANALYZE=0\n',0,False)['status'],'ENV_ERROR')

    def test_no_arbitrary_feedback(self):
        value=validate_observation({'status':'PASS','diagnostics':[{'code':'LINT-1','message':'SECRET'}],'netlist':'SECRET','functional_correctness_checked':True})
        self.assertNotIn('SECRET',json.dumps(value));self.assertFalse(value['functional_correctness_checked'])
        self.assertEqual(validate_observation({'status':'PASS','diagnostics':[{'code':'SECRET'}]})['status'],'ENV_ERROR')

    def test_missing_environment_never_launches_tool(self):
        import os
        from unittest.mock import patch
        from environment.synthesis_tools import run
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'bridge.sv';source.write_text('module bridge(input clk); endmodule')
            with patch.dict(os.environ,{'PB_CONFIG':str(root/'missing.json')}),patch('environment.synthesis_tools.subprocess.run') as launch:
                result=run(source,root/'result')
            self.assertEqual(result['observation']['status'],'ENV_ERROR');self.assertIsNone(result['reward'])
            launch.assert_not_called()

    def test_timeout_and_environment_failure_consume_attempt_budget(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);work=root/'work';work.mkdir()
            (work/'bridge.sv').write_text('module bridge; endmodule');(work/'spec.md').write_text('spec')
            calls=[]
            def backend(*args):
                calls.append(args);raise RuntimeError('SECRET infrastructure path')
            s=session_class('axil_to_apb4_queue_003')(load('test_diagnostic'),work,root/'out',[],synthesizer=backend)
            for file in ('spec.md','bridge.sv'):s.handle({'tool':'read','file':file})
            for remaining in (1,0):
                obs=s.handle({'tool':'synth_check'});self.assertEqual(obs['status'],'ENV_ERROR')
                self.assertEqual(obs['remaining_synth_calls'],remaining);self.assertNotIn('SECRET',json.dumps(obs))
            self.assertEqual(s.handle({'tool':'synth_check'})['status'],'REJECTED');self.assertEqual(len(calls),2)

    def test_formal_incomplete_is_not_failure(self):
        self.assertEqual(formal_result('PB_EQUIVALENCE=0\nVerification FAILED\n12 Aborted compare points',0)['status'],'ENV_ERROR')
        self.assertEqual(formal_result('PB_EQUIVALENCE=0\nVerification FAILED\n2 Failing compare points',0)['status'],'FAIL')
        self.assertEqual(formal_result('PB_EQUIVALENCE=1\nVerification SUCCEEDED\n8 Passing compare points',0)['status'],'PASS')
        self.assertEqual(formal_result('PB_EQUIVALENCE=1\nVerification SUCCEEDED\n8 Passing compare points',124)['status'],'ENV_ERROR')

    def test_measurement_scope(self):
        text='PB_PT_DONE=1\nPB_PT_LINK=1\nPB_PT_PATHS=1\nPB_PT_SLACK=1.5\nTotal Power\nError: thresholds (DBR-207)\n'
        value=measurement_result(text,0)
        self.assertEqual(value['status'],'TEACHING_MEASUREMENT');self.assertFalse(value['usable_for_terminal_reward'])
        for log in (text+'Error: tool (PT-063)\n',text.replace('1.5','NaN'),text.replace('PB_PT_DONE=1','PB_PT_DONE=0')):
            self.assertEqual(measurement_result(log,0)['status'],'ENV_ERROR')

    def test_session_boundaries(self):
        for task in ('axil_to_apb4_queue_003','axil_to_apb4_decoupled_004'):
            with tempfile.TemporaryDirectory() as d:
                root=Path(d);work=root/'work';work.mkdir()
                (work/'bridge.sv').write_text('module bridge; endmodule');(work/'spec.md').write_text('spec')
                calls=[]
                def backend(*a):
                    calls.append(a);return {'status':'PASS','diagnostics':[],'secret':'SECRET'}
                s=session_class(task)(load('test_diagnostic'),work,root/'out',[],synthesizer=backend)
                self.assertEqual(s.handle({'tool':'synth_check'})['status'],'REJECTED');self.assertEqual(len(calls),0)
                for file in ('spec.md','bridge.sv'):s.handle({'tool':'read','file':file})
                for file in ('private/reward.json','policy.json','mapped.v'):
                    self.assertEqual(s.handle({'tool':'read','file':file})['status'],'REJECTED')
                self.assertEqual(s.handle({'tool':'synth_check','script':'SECRET'})['status'],'REJECTED')
                for remaining in (1,0):
                    obs=s.handle({'tool':'synth_check'});self.assertEqual(obs['remaining_synth_calls'],remaining)
                    self.assertNotIn('SECRET',json.dumps(obs))
                self.assertEqual(s.handle({'tool':'synth_check'})['reason'],'synth_budget_exhausted');self.assertEqual(len(calls),2)
                self.assertEqual(s.handle({'tool':'submit'})['status'],'SUBMITTED')
                self.assertEqual(s.handle({'tool':'synth_check'})['reason'],'episode_closed');self.assertEqual(len(calls),2)

if __name__=='__main__':unittest.main()
