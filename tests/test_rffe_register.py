import unittest
from task_families.rffe_register_v1.generate import rtl,controls
from verifier.rffe_register.campaign import source_policy,interpret
from verifier.rffe_register.corpus import corpus,update

class RffeRegisterTests(unittest.TestCase):
    def test_semantic_anchors(self):
        self.assertEqual(update(0x81,0x42,'rw'),0x42)
        self.assertEqual(update(0xff,0x42,'w1c'),0xbd)
        self.assertEqual(update(0xbd,0x42,'w1c'),0xbd)
        self.assertEqual(update(0xbd,0,'w1c'),0xbd)
        self.assertEqual(update(0xbd,255,'w1c'),0)
    def test_actual_rows_and_phase_separation(self):
        for mode in ('rw','w1c'):
            seen=[]
            for phase in ('public','terminal','evaluation'):
                rows,c=corpus(mode,phase);seen.append(rows)
                self.assertEqual(c['frames'],sum(k!=2 for k,_,_ in rows))
                self.assertEqual(c['reads'],sum(k==0 for k,_,_ in rows))
                self.assertEqual(c['resets'],sum(k==2 for k,_,_ in rows))
                self.assertEqual({a for k,a,_ in rows if k==0},set(range(16)))
            self.assertNotEqual(seen[0],seen[1]);self.assertNotEqual(seen[1],seen[2])
    def test_source_interface(self):
        for mode in ('rw','w1c'):
            for source in [rtl(mode),rtl(mode,True)]+list(controls(mode).values()):self.assertIsNone(source_policy(source))
        self.assertEqual(source_policy(rtl('rw').replace('input logic clk','input logic [1:0] clk')),'fixed_interface')
        self.assertIsNotNone(source_policy(rtl('rw')+'\ninitial $finish;'))
    def test_complete_activity_not_exit_status(self):
        _,c=corpus('rw','public')
        log='PB_RFFE_COMPLETE frames=%d reads=%d resets=%d\n'%(c['frames'],c['reads'],c['resets'])+'UVM_WARNING : 0\nUVM_ERROR : 0\nUVM_FATAL : 0\n'
        self.assertEqual(interpret(log,0,c)['reward'],1)
        self.assertIsNone(interpret('',0,c)['reward'])
        self.assertIsNone(interpret(log.replace('UVM_ERROR : 0','UVM_ERROR : 1'),0,c)['reward'])
        self.assertIsNone(interpret(log,124,c)['reward'])
        self.assertEqual(interpret('PB_RFFE_MISMATCH pin data mismatch\n',0,c)['reward'],0)
        self.assertEqual(interpret('PB_RFFE_MISMATCH park must release\n',0,c)['category'],'protocol_timing_error')

if __name__=='__main__':unittest.main()
