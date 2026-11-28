import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from scripts.package_exchange import export
from scripts.package_costs import grade_cost

class EvidenceExchange(unittest.TestCase):
    def test_started_incomplete_is_retained_but_not_fabricated(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);plan=root/'plan.json';plan.write_text(json.dumps({'trials':[{'trial_id':'one','task_id':'sample'}]}))
            run=root/'runs/one';run.mkdir(parents=True);(run/'started.json').write_text('{}')
            with patch('scripts.package_exchange.replay',side_effect=ValueError('not complete')):
                r=export(plan,root/'runs',root/'exchange')
            self.assertEqual(r['started_records'],1);self.assertEqual(r['records'],0)
            record=json.loads((root/'exchange/research/started.jsonl').read_text())
            self.assertFalse(record['training_exported'])
            self.assertEqual((root/'exchange/training/rollouts.jsonl').read_text(),'')
            self.assertEqual((root/'exchange/evaluation/heldout.jsonl').read_text(),'')

    def test_reported_cpu_is_not_wall_time_and_absence_not_zero(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp);(p/'result.json').write_text(json.dumps({'compile_exit':0,'cases':[{'name':'case'}]}));(p/'case').mkdir()
            (p/'compile.log').write_text('CPU time: 137.339 seconds to compile + .386 seconds to elab + 1.828 seconds to link\n')
            (p/'case/simulation.log').write_text('CPU Time: 0.650 seconds;\n')
            r=grade_cost(p);self.assertAlmostEqual(r['compile_cpu_seconds_reported'],139.553);self.assertEqual(r['simulation_cpu_seconds_reported'],.650)
            self.assertIsNone(r['compile_wall_seconds'])
            (p/'case/simulation.log').write_text('interrupted')
            self.assertIsNone(grade_cost(p)['simulation_cpu_seconds_reported'])

if __name__=='__main__':unittest.main()
