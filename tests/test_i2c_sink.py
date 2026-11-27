import unittest
from verifier.i2c_sink.campaign import interpret,source_policy
from verifier.i2c_sink.corpus import corpus,encode
from task_families.i2c_sink_v1.generate_v2 import rtl,controls

class I2CSinkTest(unittest.TestCase):
    def test_complete_requires_activity_and_clean_vip(self):
        f=corpus('byte','public')
        done='PB_I2C_COMPLETE frames=8 bytes=51 items=51 acks=59 odd=5\n'
        clean='UVM_WARNING : 0\nUVM_ERROR : 0\nUVM_FATAL : 0\n'
        self.assertEqual(interpret(done+clean,0,'byte',f)['reward'],1)
        for log in (clean,done,done+clean+done,done+clean.replace('ERROR : 0','ERROR : 1')):
            self.assertIsNone(interpret(log,0,'byte',f)['reward'])
    def test_fail_vs_environment(self):
        f=corpus('word','public')
        self.assertEqual(interpret('PB_I2C_FAIL missing delivery\n',0,'word',f)['reward'],0)
        self.assertIsNone(interpret('PB_I2C_INFRA input\n',0,'word',f)['reward'])
        self.assertIsNone(interpret('PB_I2C_FAIL missing delivery\n',124,'word',f)['reward'])
        self.assertEqual(interpret('PB_I2C_FAIL ack hold window\n',0,'word',f)['category'],'protocol_timing_error')
    def test_candidates_restricted(self):
        self.assertIsNone(source_policy(rtl('byte')))
        for text in ('',rtl('word')+'\ninitial $finish;',rtl('byte').replace('item_data','other')):
            self.assertIsNotNone(source_policy(text))
    def test_boundaries_and_splits(self):
        a=corpus('word','public');b=corpus('word','terminal')
        self.assertEqual([len(f) for f in a],[1,2,3,4,7,16,17,1])
        self.assertNotEqual(a,b)
        self.assertTrue(encode('word',a).startswith('1 8 51 23\n'))
        self.assertIn('partial_word_crosses_stop',controls('word'))

if __name__=='__main__':unittest.main()
