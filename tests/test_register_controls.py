import json
import tempfile
import unittest
from pathlib import Path
from environment.register_instance_controls import inputs,accepted
from task_families.apb_register_v1.generate import generate

C={'task_id':'apb_register_controltest_v1','wait_cycles':0,'registers':[
    {'address':0,'reset':0x12345678,'write_mask':0xffffffff,'access':'rw'},
    {'address':12,'reset':0xffff00ff,'write_mask':0xffffffff,'access':'w1c'}]}


class ControlTests(unittest.TestCase):
    def test_manifest_omission_cannot_remove_required_dependency(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'package';generate(C,p)
            c,meta=inputs(p);self.assertEqual(c,C)
            self.assertEqual(len(meta['negative_controls']),5)
            m=json.loads((p/'manifest.json').read_text())
            m['files'].pop('verification/tb.sv')
            (p/'manifest.json').write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError,'dependency'):inputs(p)

    def test_changed_reference_rejected_before_execution(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'package';generate(C,p)
            (p/'fixtures/reference.sv').write_text('module bridge; endmodule')
            with self.assertRaisesRegex(ValueError,'source changed'):inputs(p)

    def test_old_checker_cannot_silently_inherit_current_execution(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'package';generate(C,p)
            m=json.loads((p/'manifest.json').read_text());m['producer_files']['tb.sv.in']='0'*64
            (p/'manifest.json').write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError,'version differs'):inputs(p)

    def test_negative_requires_actual_functional_or_timing_failure(self):
        for category in ('compile_error','invalid_submission','test_timeout','infrastructure_error','infrastructure_timeout'):
            self.assertFalse(accepted({'reward':0,'category':category},False))
        self.assertTrue(accepted({'reward':0,'category':'transaction_functional_error'},False))
        self.assertTrue(accepted({'reward':0,'category':'protocol_timing_error'},False))
        self.assertFalse(accepted({'reward':1,'verification_complete':False},True))
        self.assertTrue(accepted({'reward':1,'verification_complete':True},True))


if __name__=='__main__':unittest.main()
