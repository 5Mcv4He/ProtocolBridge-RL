import json
from pathlib import Path
import tempfile
import unittest
from task_families.fifo_checker_v1.generate_v3 import produce, negative_controls
from verifier.fifo_checker.model_v2 import annotate, corpus
from verifier.fifo_checker.campaign_v3 import source_policy


class CheckerGenerationV3Tests(unittest.TestCase):
    def test_single_slot_retires_old_identity_and_keeps_replacement(self):
        events=[[0,0,0,0,0],[1,1,0,7,0],[1,1,1,9,7],[1,0,1,0,9],
                [1,1,1,5,5],[1,0,0,0,0],[0,0,0,0,0]]
        rows,_=annotate(events,1)
        self.assertEqual([r[-1] for r in rows],[0,0,0,0,1,1,0])

    def test_five_slot_capacity_is_not_four_or_eight(self):
        events=[[0,0,0,0,0]]+[[1,1,0,i,0] for i in range(5)]+[[1,1,1,99,0],[1,1,0,8,0]]
        rows,c=annotate(events,5)
        self.assertEqual([r[-1] for r in rows],[0]*7+[1])
        self.assertEqual(c['full_exchange'],1)
        self.assertEqual(c['overflow'],1)

    def test_generation_domain_and_applicable_controls(self):
        self.assertNotIn('forget_pop_pointer',negative_controls(1))
        self.assertIn('discard_replacement',negative_controls(1))
        self.assertIn('binary_wrap',negative_controls(5))
        self.assertIn('narrow_count',negative_controls(5))
        with tempfile.TemporaryDirectory() as t:
            for depth in (1,5):
                out=Path(t)/str(depth);manifest=produce(depth,out)
                task=json.loads((out/'task.json').read_text())
                self.assertEqual(task['verifier_revision'],3)
                self.assertEqual(set(manifest['files']),{str(p.relative_to(out)) for p in out.rglob('*') if p.is_file() and p.name!='generation.json'})
                self.assertIsNone(source_policy((out/'reference.sv').read_text()))
                self.assertIsNone(source_policy((out/'alternate.sv').read_text()))
                self.assertEqual(len(list((out/'controls').glob('*.sv'))),len(negative_controls(depth)))
            for invalid in (0,2,3,4,6,True):
                with self.assertRaises(ValueError):produce(invalid,Path(t)/'bad')
            self.assertFalse((Path(t)/'bad').exists())

    def test_phase_obligations_derive_from_actual_rows(self):
        for depth in (1,5):
            for phase in ('public','terminal','evaluation'):
                rows,c=corpus(depth,phase)
                self.assertTrue(all(c.values()))
                again,observed=annotate([r[:5] for r in rows],depth)
                self.assertEqual(rows,again)
                self.assertEqual(c,observed)
                self.assertGreater(c['identity_after_reuse'],0)


if __name__=='__main__':unittest.main()
