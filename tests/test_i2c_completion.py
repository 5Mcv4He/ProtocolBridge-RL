import tempfile,unittest,json
from pathlib import Path
from task_families.i2c_completion_v1.generate import generate,scaffold
from task_families.i2c_sink_v1.qualification import check
from verifier.i2c_sink.campaign import source_policy,ROOT
class CompletionTests(unittest.TestCase):
 def test_scaffold_withholds_delivery(self):
  s=scaffold();self.assertIsNone(source_policy(s))
  self.assertNotIn('logic half',s);self.assertNotIn('logic [7:0] first',s)
  self.assertNotIn('item_valid<=1',s);self.assertIn('drive_delay<=35',s)
  for event in ('BYTE_ACCEPTED','START boundary','STOP boundary'):self.assertIn(event,s)
 def test_existing_gate_still_matches(self):
  for m in ('byte','word'):self.assertTrue(check(ROOT/'tasks'/('i2c_sink_'+m+'_v1'))['admitted'])
 def test_canonical_instance(self):
  for m in ('byte','word'):
   with tempfile.TemporaryDirectory() as t:
    p=Path(t)/'task';meta=generate(m,p);self.assertEqual(meta['backend_contract_id'],'i2c_sink_'+m+'_v1')
    expected=ROOT/'tasks'/meta['task_id']
    for f in p.rglob('*'):
     if f.is_file():self.assertEqual(f.read_bytes(),(expected/f.relative_to(p)).read_bytes())
if __name__=='__main__':unittest.main()
