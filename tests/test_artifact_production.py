import json,tempfile,unittest
from pathlib import Path
from verification_resources.production import materialize,check
from environment.artifact_task.session import sha
class Production(unittest.TestCase):
 def test_canonical_contract_and_dependencies_cannot_be_replaced(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'p';materialize('reference-repair','wrap',p);check(p)
   manifest=json.loads((p/'manifest.json').read_text());original=json.loads(json.dumps(manifest))
   (p/'task/spec.md').write_text('Changed requirements')
   manifest['files']['task/spec.md']=sha(p/'task/spec.md');(p/'manifest.json').write_text(json.dumps(manifest))
   with self.assertRaises(ValueError):check(p)
   (p/'manifest.json').write_text(json.dumps(original))
   with self.assertRaises(ValueError):check(p)
 def test_missing_qualified_dependency_and_superseded_uart_reject(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'p';materialize('uart-transmit','8n1',p);m=json.loads((p/'manifest.json').read_text())
   m['verifier_revision']=1;(p/'manifest.json').write_text(json.dumps(m))
   with self.assertRaises(ValueError):check(p)
   m['verifier_revision']=3;m['source_dependencies'].pop('verifier/uart_tx/tb_v3.sv');(p/'manifest.json').write_text(json.dumps(m))
   with self.assertRaises(ValueError):check(p)
 def test_unknown_combination_rejected(self):
  with tempfile.TemporaryDirectory() as t:
   with self.assertRaises(ValueError):materialize('uart-transmit','16bit',Path(t)/'p')
