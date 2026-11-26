import hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from task_families.router_v1.report import report,numeric_cost
class AdmissionProjection(unittest.TestCase):
 def test_missing_source_binding_cannot_be_published_as_admitted(self):
  with tempfile.TemporaryDirectory() as tmp:
   d=Path(tmp);f={'task_id':'x2p_router_compact_v1','files':{}};(d/'freeze.json').write_text(json.dumps(f))
   r={'accepted':True,'task_id':f['task_id'],'freeze_sha256':hashlib.sha256((d/'freeze.json').read_bytes()).hexdigest()};(d/'result.json').write_text(json.dumps(r))
   m={'task_id':f['task_id'],'files':{'environment/policy.py':'frozen-code'}}
   with patch('task_families.router_v1.report.verify',return_value=m):
    with self.assertRaisesRegex(ValueError,'Incomplete gate source binding'):report(d,d)
 def test_rejected_gate_stays_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   d=Path(tmp);(d/'freeze.json').write_text('{}');(d/'result.json').write_text('{"accepted":false}')
   with patch('task_families.router_v1.report.verify',return_value={}):
    with self.assertRaisesRegex(ValueError,'Unaccepted'):report(d,d)

class CostProjection(unittest.TestCase):
 def test_missing_footers_are_not_zero_and_cpu_is_measured(self):
  with tempfile.TemporaryDirectory() as d:
   self.assertIsNone(numeric_cost(d)['compiler_cpu_seconds_measured'])
   p=Path(d);(p/'compile.log').write_text('CPU time: 1 seconds to compile + 2 seconds to elab + 3 seconds to link\n')
   (p/'simulation.log').write_text('CPU Time: 2.4 seconds; Data structure size: 4.5Mb\n')
   x=numeric_cost(d);self.assertEqual(x['compiler_cpu_seconds_measured'],6);self.assertEqual(x['simulator_cpu_seconds_measured'],2.4)
