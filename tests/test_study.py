import json,tempfile,unittest
from pathlib import Path
from environment.policy import load,prompt,parse_action
from environment.batch_contract import experiment_prompt,PROTOCOLS
from environment.policy_session import Session
from scripts.batch_analysis import interval
from scripts.batch_tables import aggregate

class InteractionVersionTests(unittest.TestCase):
    def test_v1_prompt_is_unchanged_and_v2_c_e_are_identical(self):
        for mode in ('spec_only','test_verdict','test_diagnostic'):
            self.assertEqual(experiment_prompt(load(mode)),prompt(load(mode)))
        self.assertEqual(experiment_prompt(load('test_verdict'),protocol=PROTOCOLS[1]),experiment_prompt(load('test_diagnostic'),protocol=PROTOCOLS[1]))
        with self.assertRaises(ValueError):experiment_prompt(load('spec_only'),protocol='unknown')
    def test_extra_edit_fields_stay_rejected_and_have_actionable_v2_help(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);work=root/'work';work.mkdir();(work/'spec.md').write_text('spec');original='module bridge; endmodule';(work/'bridge.sv').write_text(original)
            calls=[]
            def grader(*args,**kwargs):calls.append(args);return {'reward':0,'category':'transaction_functional_error','failed_case':'address_data'}
            for mode in ('spec_only','test_verdict','test_diagnostic'):
                s=Session(load(mode),work,root/mode,[],grader);s.protocol_version=2
                for f in ('spec.md','bridge.sv'):s.handle({'tool':'read','file':f})
                obs=s.handle({'tool':'edit','content':'changed','content_note':'overwrite'})
                self.assertEqual(obs['reason'],'invalid_action');self.assertEqual(s.actions,3);self.assertEqual(s.edits,0)
                self.assertEqual((work/'bridge.sv').read_text(),original);self.assertEqual(calls,[])
                self.assertEqual(obs['action_fields']['edit'],['content','tool']);self.assertEqual(set(obs['action_fields']),set(s.policy['allowed_tools']))
                # Atomic parsing is still strict; no valid prefix action is executed.
                with self.assertRaises(ValueError):parse_action('{"tool":"test"}\n{"tool":"submit"}')
    def test_public_projection_does_not_depend_on_action_protocol(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);work=root/'work';work.mkdir();(work/'bridge.sv').write_text('module bridge; endmodule')
            for mode in ('test_verdict','test_diagnostic'):
                values=[]
                for v in (1,2):
                    s=Session(load(mode),work,root/(mode+str(v)),[],lambda *a,**k:{'reward':0,'category':'transaction_functional_error','failed_case':'address_data'})
                    s.protocol_version=v;values.append(s.handle({'tool':'test'}))
                self.assertEqual(*values)

class StatisticalAccountingTests(unittest.TestCase):
    def test_wilson_bounds_and_empty_denominator(self):
        self.assertIsNone(interval(0,0));self.assertAlmostEqual(interval(0,10)[1],.2775401687666165)
        self.assertAlmostEqual(interval(10,10)[0],.7224598312333834)
    def test_missing_candidate_and_token_measurements_are_unknown_not_rtl_failures(self):
        x=aggregate([{'reward':None,'protocol_errors':1,'labels':['agent_incomplete']}])
        self.assertEqual(x['first_candidate_unmeasured'],1);self.assertEqual(x['first_candidate_public_fail'],0)
        self.assertIsNone(x['tokens']['totalTokens']);self.assertIsNone(x['api_currency_cost'])

if __name__=='__main__':unittest.main()
