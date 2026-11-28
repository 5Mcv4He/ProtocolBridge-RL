import hashlib,json,tempfile,unittest
from pathlib import Path
from environment.artifact_task.session_v4 import Session,sha
from environment.native_tools.controller import Controller

class NativeGate(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        p=Path(self.tmp.name);self.work=p/'work';self.work.mkdir()
        (self.work/'candidate.sv').write_text('initial');(self.work/'spec.md').write_text('spec')
        self.grades=[]
        def grade(path,out,phase):
            self.grades.append((phase,sha(path)))
            return {'reward':0,'category':'transaction_mismatch','source_sha256':sha(path),'secret':'NEVER_EXPOSE'}
        self.s=Session({'task_id':'gate','deliverable':'candidate.sv'},self.work,p/'out',grade,max_actions=20,max_tests=2)
        self.c=Controller(self.s);self.serial=0
    def call(self,name,args=None):
        self.serial+=1
        return self.c.dispatch({'kind':'tool_request','call_id':str(self.serial),'name':name,'arguments':args if args is not None else {}})
    def reads(self):
        self.call('read',{'file':'spec.md'});self.call('read',{'file':'candidate.sv'})
    def test_exact_edit_and_feedback_binding(self):
        self.reads();source='module candidate;\nendmodule\n'
        edit=self.call('edit',{'content':source});tested=self.call('test')
        self.assertEqual((self.work/'candidate.sv').read_text(),source)
        self.assertEqual(edit['observation']['source_sha256'],tested['observation']['source_sha256'])
        self.call('edit',{'content':'changed'})
        self.assertNotEqual(sha(self.work/'candidate.sv'),tested['observation']['source_sha256'])
        self.assertNotIn('NEVER_EXPOSE',json.dumps(tested))
    def test_extra_fields_never_execute(self):
        self.reads()
        for args in ({'content':'bad','file':'candidate.sv'},{'tool':'submit','content':'bad'},{'content':['bad']}):
            self.assertEqual(self.call('edit',args)['observation']['status'],'REJECTED')
        self.assertEqual((self.work/'candidate.sv').read_text(),'initial')
        self.assertEqual(self.s.edits,0)
    def test_unexpected_types_and_paths(self):
        for name,args in [([],{}),('read',{'file':[]}),('read',{'file':'../reference.sv'}),('shell',{'cmd':'id'}),('edit','{"content":"bad"}')]:
            self.assertEqual(self.call(name,args)['observation']['status'],'REJECTED')
    def test_budget_denies_without_grader(self):
        self.call('test');self.call('test')
        self.assertEqual(self.call('test')['observation']['reason'],'test_budget_exhausted')
        self.assertEqual(len(self.grades),2)
    def test_global_budget_closes(self):
        for _ in range(20):self.call('read',{'file':'spec.md'})
        self.assertTrue(self.s.done)
        self.assertTrue(self.call('test')['stop']);self.assertEqual(len(self.grades),0)
        self.assertEqual(self.s.actions,20)
    def test_submit_stops_same_batch_later_calls(self):
        self.reads();self.call('submit');self.call('edit',{'content':'bad'});self.call('test')
        self.assertEqual(self.s.actions,3);self.assertEqual(self.grades,[])
        self.assertEqual((self.s.out/'submission/candidate.sv').read_text(),'initial')
        with self.assertRaises(ValueError):self.s.finalize(False)
        self.assertEqual(self.s.finalize(True)['reward'],0)
        self.assertEqual(self.grades[0][0],'terminal')
    def test_replay_is_transport_failure(self):
        packet={'kind':'tool_request','call_id':'fixed','name':'test','arguments':{}}
        self.c.dispatch(packet)
        with self.assertRaises(ValueError):self.c.dispatch(packet)
        self.assertEqual(len(self.grades),1)
    def test_no_assumed_feedback_receipt(self):
        self.call('test');self.c.returned('1')
        self.assertTrue(self.c.calls[0]['transport_returned'])
        self.assertFalse(self.c.calls[0]['model_receipt_confirmed'])
        self.assertFalse(self.s.trace[0]['observation_delivered'])
    def test_infrastructure_not_functional(self):
        def broken(*a):raise RuntimeError('private path')
        self.s.grader=broken
        r=self.call('test');self.assertEqual(r['observation']['status'],'ENV_ERROR')
        self.assertNotIn('private path',json.dumps(r))
    def test_read_requirements(self):
        self.assertEqual(self.call('submit')['observation']['reason'],'read_both_first')
        self.assertFalse(self.s.submitted)

if __name__=='__main__':unittest.main()
