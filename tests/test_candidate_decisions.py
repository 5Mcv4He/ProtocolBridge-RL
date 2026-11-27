import json,tempfile,unittest
from pathlib import Path
from scripts.candidate_decisions import analyze,sha_text
class Decisions(unittest.TestCase):
    def test_same_candidate_return_and_untested_pass_are_distinct(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);d.joinpath('submission').mkdir();a='bad';b='changed';events=[]
            def event(tool,obs,**args):events.append({'action_index':len(events)+1,'action':dict(tool=tool,**args),'observation':obs,'executed':True,'observation_delivered':True})
            event('test',{'status':'FAIL'})
            event('edit',{'status':'EDITED'},content=b)
            event('edit',{'status':'EDITED'},content=a)
            event('submit',{'status':'SUBMITTED'});events[-1]['observation_delivered']=False
            (d/'freeze.json').write_text(json.dumps({'initial_rtl_sha256':sha_text(a),'policy':{'max_public_test_calls':6}}))
            (d/'metrics.json').write_text(json.dumps({'actions':4,'submitted':True,'terminal':{'reward':0},'first_candidate_public':{'reward':1}}))
            (d/'trace.json').write_text(json.dumps(events));(d/'submission/bridge.sv').write_text(a)
            x=analyze(d)
            self.assertTrue(x['submitted_previously_failed_source']);self.assertEqual(x['final_delivered_public_status'],'FAIL')
            self.assertEqual(x['untested_edit_versions'],2);self.assertEqual(x['observed_public_regressions'],[])
            self.assertEqual(x['never_publicly_tested_edited_sources'],[sha_text(b)]);self.assertEqual(x['edited_after_delivered_pass'],[]);self.assertEqual(x['unused_test_allowance'],5)
