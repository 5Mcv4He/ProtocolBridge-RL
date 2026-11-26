import hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from task_families.router_v1.report import report
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
