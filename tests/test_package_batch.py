import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from environment.native_tools.package_batch import batch,infrastructure_stop
from environment.artifact_task.session_v4 import save,sha

class ResumablePackageStudy(unittest.TestCase):
    def test_completed_not_rerun_and_changed_evidence_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);plan=root/'plan.json';save(plan,{'trials':[{'trial_id':'one'},{'trial_id':'two'}]})
            calls=[]
            def run(planfile,tid,dest,password):
                calls.append(tid);dest.mkdir()
                r={'trial_id':tid,'plan_sha256':sha(planfile),'terminal':{'reward':0,'category':'transaction_functional_error'},'error':None,'actions':7,'reported_tokens':100}
                save(dest/'result.json',r);save(dest/'events.json',[]);return r
            with patch('environment.native_tools.package_batch.unchanged',return_value=True),patch('environment.native_tools.package_batch.run',side_effect=run):
                self.assertEqual(batch(plan,root/'out')['completed'],2)
                self.assertEqual(batch(plan,root/'out')['completed'],2)
                self.assertEqual(calls,['one','two'])
                save(root/'out/one/events.json',[{'changed':True}])
                with self.assertRaises(ValueError):batch(plan,root/'out')
                self.assertEqual(calls,['one','two'])

    def test_unfinished_directory_never_restarted(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);plan=root/'plan.json';save(plan,{'trials':[{'trial_id':'one'}]});(root/'out/one').mkdir(parents=True)
            with patch('environment.native_tools.package_batch.unchanged',return_value=True),patch('environment.native_tools.package_batch.run') as run:
                with self.assertRaises(RuntimeError):batch(plan,root/'out')
                run.assert_not_called()

    def test_heldout_environment_failure_stops_sampling(self):
        self.assertTrue(infrastructure_stop({'terminal':{'reward':1},'reserved_evaluation':{'category':'infrastructure_error'}}))
        self.assertFalse(infrastructure_stop({'terminal':{'reward':0,'category':'test_timeout'}}))

if __name__=='__main__':unittest.main()
