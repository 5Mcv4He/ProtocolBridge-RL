import json
import tempfile
import unittest
from pathlib import Path
from scripts.control_costs import summarize,sha


class ControlCosts(unittest.TestCase):
    def fixture(self,root):
        c=root/'controls';c.mkdir();(c/'freeze.json').write_text('{}');rows=[]
        for i,label in enumerate(('reference-0-full','reference-0-public')):
            p=c/label;p.mkdir();d=p/'activity';d.mkdir()
            (d/'simulation.log').write_text('CPU Time: 2.50 seconds;\n')
            r=dict(reward=1,category='pass',verification_complete=True,cases=[{'name':'activity'}])
            if i:r['compile_reused']=True
            else:
                r['compile_exit']=0
                (p/'compile.log').write_text('CPU time: 10 seconds to compile + 2 seconds to elab + 3 seconds to link\n')
            (p/'result.json').write_text(json.dumps(r));(p/'backend.json').write_text(json.dumps({'inputs':{'candidate':'same-bank','environment':'same'}}))
            rows.append(dict(label=label,reward=1,category='pass',verification_complete=True,cases_executed=1,compile_reused=bool(i),wall_seconds=20,result_sha256=sha(p/'result.json')))
        report=dict(schema='router-instance-controls-v2',task_id='fixture',controls_passed=True,rows=rows,freeze_sha256=sha(c/'freeze.json'))
        (c/'result.json').write_text(json.dumps(report));return report

    def test_one_compile_two_actual_simulations(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);self.fixture(root);r=summarize(root)
            self.assertEqual((r['actual_compile_attempts'],r['reused_compile_runs'],r['simulation_attempts']),(1,1,2))
            self.assertEqual(r['compile_cpu_seconds_reported'],15)
            self.assertEqual(r['simulation_cpu_seconds_reported'],5)
            self.assertIsNone(r['job_wall_seconds']);self.assertFalse(r['admission_inferred'])

    def test_wrong_reuse_and_duplicate_rows_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);r=self.fixture(root)
            p=root/'controls/reference-0-public/backend.json';original=p.read_text();p.write_text('{"inputs":{"candidate":"different"}}')
            with self.assertRaises(ValueError):summarize(root)
            p.write_text(original);r['rows'].append(r['rows'][0]);(root/'controls/result.json').write_text(json.dumps(r))
            with self.assertRaises(ValueError):summarize(root)

    def test_missing_cpu_measurement_not_zero(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);self.fixture(root);(root/'controls/reference-0-public/activity/simulation.log').write_text('No CPU report')
            r=summarize(root);self.assertIsNone(r['simulation_cpu_seconds_reported']);self.assertFalse(r['simulation_cpu_reports_complete'])


if __name__=='__main__':unittest.main()
