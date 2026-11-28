import json,tempfile,unittest
from pathlib import Path
from environment.package_session import Session
from environment.artifact_task.session_v4 import sha
from environment.native_tools.controller_v3 import Controller

class RouterSession(unittest.TestCase):
    def test_watchdog_is_functional_and_process_timeout_is_infrastructure(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);work=root/'work';work.mkdir();(work/'bridge.sv').write_text('initial');(work/'spec.md').write_text('spec')
            results=[(0,'test_timeout'),(None,'infrastructure_error')]
            def grade(path,out,phase):
                reward,category=results.pop(0);return dict(reward=reward,category=category,source_sha256=sha(path))
            session=Session({'task_id':'test','deliverable':'bridge.sv'},work,root/'session',grade)
            controller=Controller(session)
            for i,expected in enumerate(('FAIL','ENV_ERROR')):
                obs=controller.dispatch(dict(kind='tool_request',call_id=str(i),name='test',arguments='{}'))['observation']
                self.assertEqual(obs['status'],expected)
                self.assertEqual(obs['source_sha256'],sha(work/'bridge.sv'))
            trace=json.loads((root/'session/trace.json').read_text())
            self.assertEqual(trace[0]['observation']['category'],'test_timeout')

    def test_budget_and_submit_still_stop_before_terminal(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);work=root/'work';work.mkdir();(work/'bridge.sv').write_text('initial');(work/'spec.md').write_text('spec');calls=[]
            def grade(path,out,phase):
                calls.append(phase);return dict(reward=0,category='transaction_functional_error',source_sha256=sha(path))
            session=Session({'task_id':'test','deliverable':'bridge.sv'},work,root/'session',grade,max_tests=2)
            for _ in range(3):session.handle({'tool':'test'})
            self.assertEqual(calls,['public','public'])
            for name in ('spec.md','bridge.sv'):session.handle({'tool':'read','file':name})
            session.handle({'tool':'submit'})
            self.assertEqual(session.handle({'tool':'edit','content':'late'})['reason'],'episode_closed')
            with self.assertRaises(ValueError):session.finalize(False)
            self.assertEqual(calls,['public','public'])
            self.assertEqual(session.finalize(True)['reward'],0)
            self.assertEqual(calls,['public','public','terminal'])

if __name__=='__main__':unittest.main()
