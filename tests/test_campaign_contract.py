"""Unit checks for grading/plan integrity, not substitutes for EDA evidence."""
import tempfile,unittest
from pathlib import Path
from verifier.campaign import interpret,source_policy
from verifier.scenarios import suite

class GradingContract(unittest.TestCase):
    def setUp(self):
        self.case=suite(True)[0];n=len(self.case['rows'])
        self.log=('PB3_SEQUENCE '+self.case['sequence']+'\nPB3_DONE\n'
                  'PB3_RESULT planned=%d axi=%d apb=%d checked=%d aborted=0 aborted_apb=0 errors=0\n'%(n,n,n,n)
                  +'UVM_ERROR : 0\nUVM_FATAL : 0\n'+'PB3_LATENCY accept_to_setup=2 completion_to_valid=1 waits=0 stalls=0\n'*n)
    def test_complete_result(self):self.assertEqual(interpret(self.log,0,self.case)['reward'],1)
    def test_missing_completion_is_failure(self):
        self.assertEqual(interpret(self.log.replace('axi=8','axi=7'),0,self.case)['reward'],0)
    def test_infrastructure_precedes_timeout(self):
        self.assertIsNone(interpret('PB_INFRA license\nPB3_TIMEOUT',0,self.case)['reward'])
    def test_interrupted_execution_is_indeterminate(self):
        self.assertIsNone(interpret('',143,self.case)['reward'])
    def test_explicit_cycle_timeout(self):
        self.assertEqual(interpret('PB3_TIMEOUT',0,self.case)['category'],'test_timeout')
    def test_wrong_sequence_cannot_pass(self):
        self.assertIsNone(interpret(self.log.replace(self.case['sequence'],'unknown'),0,self.case)['reward'])
    def test_empty_case_cannot_pass(self):
        self.assertIsNone(interpret(self.log,0,dict(self.case,rows=[]))['reward'])
    def test_stimulus_mismatch_cannot_pass(self):
        self.assertIsNone(interpret(self.log.replace('stalls=0','stalls=1'),0,self.case)['reward'])
    def test_vip_protocol_error_before_early_exit(self):
        log='UVM_ERROR monitor [register_fail:AMBA:AXI3:signal_stable_rdata_when_rvalid_high_check]'
        self.assertEqual(interpret(log,0,self.case)['category'],'protocol_timing_error')
    def test_reset_accounting(self):
        c=next(x for x in suite(True) if x['name']=='reset_b_stall')
        log='PB3_SEQUENCE reset_abort_sequence\nPB3_DONE\nPB3_RESET stage=7\nPB3_RESET_OFFSET cycles=0\nPB3_RESULT planned=6 axi=5 apb=6 checked=5 aborted=1 aborted_apb=1 errors=0\nUVM_ERROR : 0\nUVM_FATAL : 0\n'
        log+='PB3_LATENCY accept_to_setup=2 completion_to_valid=1 waits=0 stalls=1\n'*5
        self.assertEqual(interpret(log,0,c)['reward'],1)
        self.assertEqual(interpret(log.replace('aborted_apb=1','aborted_apb=0'),0,c)['reward'],0)
    def test_submission_side_effect_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bridge.sv'
            for body in ('initial $finish;', 'initial $system("id");', 'assign a=tb.private_value;', 'import uvm_pkg::*;'):
                p.write_text('module bridge;'+body+'endmodule')
                self.assertIsNotNone(source_policy(p))

class ScenarioContract(unittest.TestCase):
    def test_all_vectors_are_legal_and_reproducible(self):
        self.assertEqual(suite(seed=27),suite(seed=27))
        self.assertNotEqual(suite(seed=27),suite(seed=28))
        for c in suite():
            for w,a,d,st,ad,wd,wait,stall,e,abort,gap in c['rows']:
                self.assertEqual(a%4,0);self.assertIn(w,(0,1));self.assertIn(e,(0,1))
                self.assertTrue(0<=st<=15 and 0<=a<2**32 and 0<=d<2**32)
                self.assertFalse(ad and wd)
                self.assertIn(abort%100,range(9))
    def test_required_cross_is_enumerated(self):
        rows=[r for c in suite() if c['name'].startswith('strobe_cross') for r in c['rows']]
        seen={(r[3],2 if r[4] else 1 if r[5] else 0,r[8],0 if not r[6] else 1 if r[6]<=8 else 2,int(r[7]>0)) for r in rows if r[0]}
        self.assertEqual(len(seen),576)
    def test_reset_positions_and_multiple_random_streams(self):
        cases=suite();self.assertEqual(sum(c['name'].startswith('random_stream_') for c in cases),4)
        for c in cases:
            if c['name'].startswith('reset_'):
                offsets={r[9]//100 for r in c['rows'] if r[9]}
                self.assertEqual(offsets,{0} if 'setup' in c['name'] else {0,1,7,31})

if __name__=='__main__':unittest.main()
