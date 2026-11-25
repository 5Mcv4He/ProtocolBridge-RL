import json,tempfile,unittest
from pathlib import Path
from scripts.export_rollout_exchange import ROOT,export
class EngineeringExchange(unittest.TestCase):
 def test_v1_rejects_new_capabilities_before_output(self):
  with tempfile.TemporaryDirectory() as d:
   out=Path(d)/'out'
   with self.assertRaisesRegex(ValueError,'schema 2'):export([ROOT/'experiments/engineering-tools-v1/tools'],out)
   self.assertFalse(out.exists())
 def test_v2_preserves_actual_feedback_and_reward_separation(self):
  with tempfile.TemporaryDirectory() as d:
   out=Path(d)/'out';m=export([ROOT/'experiments/engineering-tools-v1/baseline',ROOT/'experiments/engineering-tools-v1/tools'],out,2)
   self.assertEqual(m['schema'],'pb-exchange-manifest-v2');self.assertEqual(m['records'],4)
   rows=[json.loads(x) for x in (out/'training/rollouts.jsonl').read_text().splitlines()]
   self.assertTrue(all(r['outcome']['reward']==0 for r in rows))
   enhanced=[r for r in rows if r['cohort']['capabilities']=='engineering-tools-v1'];self.assertEqual(len(enhanced),2)
   events=[e for r in enhanced for e in r['engineering_feedback']]
   self.assertEqual(sum(e['action']['tool']=='inspect' for e in events),4)
   self.assertEqual(sum(e['action']['tool']=='compile' for e in events),1)
   self.assertTrue(all(e['observation']['invariant']['code']=='Q_CAPACITY' for e in events if e['action']['tool']=='inspect'))
   self.assertNotIn('held_out_reward',(out/'training/rollouts.jsonl').read_text())
   self.assertEqual(sum(r['resources']['compile_calls'] for r in enhanced),1)
   schema=json.loads((ROOT/'schemas/rollout-exchange-v2.schema.json').read_text())
   for row in rows:
    self.assertEqual(row['schema'],schema['properties']['schema']['const'])
    self.assertTrue(set(schema['required'])<=set(row))
    self.assertFalse(set(row)-set(schema['properties']))
    self.assertIn(row['cohort']['capabilities'],schema['properties']['cohort']['properties']['capabilities']['enum'])
    self.assertIn('capability_sources',row['versions'])
   for name,digest in m['files'].items():
    from scripts.export_rollout_exchange import sha
    self.assertEqual(sha(out/name),digest)
if __name__=='__main__':unittest.main()
