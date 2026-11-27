import copy,json,tempfile,unittest
from pathlib import Path
from environment.policy import load,validate as legacy
from environment.verification_budget import derive,validate
from environment.verification_preflight import reuse,seal,KEYS,NAMES

class BudgetPolicy(unittest.TestCase):
    def test_only_public_budget_changes_and_legacy_stays_fixed(self):
        base=load('test_diagnostic');a=derive(base,2,legacy);b=derive(base,6,legacy)
        self.assertEqual({k for k in a if a[k]!=b[k]},{'max_public_test_calls'})
        self.assertEqual(a['version'],2);self.assertEqual(base['version'],1)
        for bad in (True,0,3,20,'6'):
            with self.assertRaises(ValueError):derive(base,bad,legacy)
        for key,value in [('max_agent_actions',21),('max_feedback_chars',4096),('readable_files',['spec.md','bridge.sv','reference.sv'])]:
            p=copy.deepcopy(b);p[key]=value
            with self.assertRaises(ValueError):validate(p,legacy)
        with self.assertRaises(ValueError):derive(load('spec_only'),6,legacy)

    def test_preflight_reuse_binds_source_tools_and_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);prior=p/'prior';prior.mkdir();manifest={k:'fixed' for k in KEYS}
            for name in NAMES:
                d=prior/name;d.mkdir();(d/'result.json').write_text('{"accepted":true}')
            seal(prior,manifest)
            dest=p/'new';dest.mkdir();reuse(dest,prior,dict(manifest,public_test_budget=6))
            self.assertTrue((dest/'preflight-reuse.json').exists())
            for key in KEYS:
                with self.assertRaises(ValueError):reuse(p/'bad',prior,dict(manifest,**{key:'changed'}))
            (prior/NAMES[0]/'result.json').write_text('{"accepted":false}')
            with self.assertRaises(ValueError):reuse(p/'bad',prior,manifest)
