"""Schema regression: confirmed I2C faults must not become infrastructure feedback."""
import json,tempfile,unittest
from pathlib import Path
from environment.artifact_task.session_v3 import Session,sha

class SessionV3Test(unittest.TestCase):
    def test_failure_projection_and_boundaries(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);work=root/'work';work.mkdir()
            (work/'spec.md').write_text('spec');(work/'i2c_sink.sv').write_text('original')
            calls=[]
            def grader(source,out,phase):
                calls.append((phase,sha(source)))
                return dict(source_sha256=sha(source),reward=0.,category='transaction_mismatch',private_vector='NEVER_VISIBLE',first_failure='secret case')
            s=Session(dict(task_id='example',deliverable='i2c_sink.sv'),work,root/'session',grader,20,1)
            s.handle(dict(tool='read',file='spec.md'));s.handle(dict(tool='read',file='i2c_sink.sv'))
            old=s.handle(dict(tool='test'))
            self.assertEqual(set(old),{'status','category','source_sha256','remaining_test_calls'})
            self.assertEqual((old['status'],old['category']),('FAIL','transaction_mismatch'))
            s.handle(dict(tool='edit',content='new'))
            self.assertNotEqual(old['source_sha256'],sha(work/'i2c_sink.sv'))
            self.assertEqual(s.handle(dict(tool='test'))['reason'],'test_budget_exhausted')
            self.assertEqual(len(calls),1)
            s.handle(dict(tool='submit'))
            self.assertEqual(s.handle(dict(tool='edit',content='later'))['reason'],'episode_closed')
            with self.assertRaises(ValueError):s.finalize(False)
            self.assertEqual(s.finalize(True)['reward'],0.)
            self.assertEqual(calls[-1],('terminal',sha(root/'session/submission/i2c_sink.sv')))
            self.assertNotIn('NEVER_VISIBLE',json.dumps(s.trace))
    def test_shared_twenty_action_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);work=root/'work';work.mkdir();(work/'i2c_sink.sv').write_text('rtl')
            s=Session(dict(task_id='example',deliverable='i2c_sink.sv'),work,root/'session',lambda *_:self.fail('not permitted'),20,4)
            for _ in range(20):s.handle(dict(tool='invalid'))
            self.assertTrue(s.done);self.assertEqual(s.actions,20)
            self.assertEqual(s.handle(dict(tool='test'))['reason'],'episode_closed')
            self.assertEqual(s.actions,20)

if __name__=='__main__':unittest.main()
