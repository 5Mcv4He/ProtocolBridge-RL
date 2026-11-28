import json,unittest
import test_controller as base
from environment.native_tools.controller_v3 import Controller
class FixedFile(unittest.TestCase):
    def setUp(self):
        self.fixture=base.NativeGate();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.s=self.fixture.s;self.c=Controller(self.s);self.serial=0
        self.call('read',{'file':'spec.md'});self.call('read',{'file':'candidate.sv'})
    def call(self,name,args):
        self.serial+=1;return self.c.dispatch({'kind':'tool_request','call_id':str(self.serial),'name':name,'arguments':json.dumps(args)})
    def test_exact_file_is_checked_not_ignored(self):
        self.assertEqual(self.call('edit',{'file':'candidate.sv','content':'new'})['observation']['status'],'EDITED')
        self.assertEqual((self.s.work/'candidate.sv').read_text(),'new')
        self.assertEqual(json.loads(self.c.calls[-1]['raw_arguments'])['file'],'candidate.sv')
    def test_missing_wrong_extra_fields_rejected(self):
        for args in ({'content':'new'},{'file':'../candidate.sv','content':'new'},{'file':'reference.sv','content':'new'},{'file':'candidate.sv','content':'new','command':'run'}):
            self.assertEqual(self.call('edit',args)['observation']['status'],'REJECTED')
        self.assertEqual(self.s.edits,0)
    def test_after_submit_cannot_edit(self):
        self.call('submit',{});self.call('edit',{'file':'candidate.sv','content':'late'})
        self.assertEqual((self.s.out/'submission/candidate.sv').read_text(),'initial')
