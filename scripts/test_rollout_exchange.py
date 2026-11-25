"""Actual reviewed evidence checks for the exchange adapter; no model/EDA calls."""
import json,tempfile,unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from export_rollout_exchange import export,validate_source,safe,sha,ROOT,training_infrastructure
class Exchange(unittest.TestCase):
 def test_real_reward_distribution_and_separation(self):
  sources=[ROOT/'experiments/batch-study-001/text-v1-stopped',ROOT/'experiments/task002-v1/pilot']
  with tempfile.TemporaryDirectory() as d:
   out=Path(d)/'exchange';m=export(sources,out)
   rows=[json.loads(x) for x in (out/'training/rollouts.jsonl').read_text().splitlines()]
   self.assertEqual(len(rows),26);self.assertEqual(len({r['episode_id'] for r in rows}),26)
   q=[r for r in rows if r['task_id']=='axil_to_apb4_router_002'];self.assertEqual(sum(r['outcome']['reward']==1 for r in q),6)
   self.assertEqual(sum(r['outcome']['reward'] is None for r in rows),1)
   self.assertNotIn('held_out_reward',(out/'training/rollouts.jsonl').read_text())
   self.assertNotIn('first_candidate_public',(out/'training/rollouts.jsonl').read_text())
   self.assertEqual(len((out/'evaluation/heldout.jsonl').read_text().splitlines()),26)
   for r in q:self.assertEqual(r['versions']['task_version'],1)
   for r in rows:
    for event in r['tool_events'] or []:
     a=event['action'].get('content_artifact')
     if a:self.assertEqual(sha(out/a['file']),a['sha256'])
   for name,h in m['files'].items():self.assertEqual(sha(out/name),h)
   with self.assertRaises(FileExistsError):export(sources,out)
 def test_heldout_failure_cannot_change_training_validity(self):
  row={'terminal_category':'pass','infrastructure':True,'environment_error_locations':['held_out','first_candidate_public']}
  self.assertFalse(training_infrastructure(row,[]))
  self.assertTrue(training_infrastructure(row,[{'observation':{'status':'ENV_ERROR'}}]))
  self.assertTrue(training_infrastructure(dict(row,terminal_category='infrastructure_error'),[]))
 def test_duplicate_sources_rejected(self):
  p=ROOT/'experiments/task002-v1/pilot'
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):export([p,p],Path(d)/'out')
 def test_escape_rejected(self):
  for p in ('../private.json','/tmp/private.json'):
   with self.assertRaises(ValueError):safe(ROOT,p)
 def test_failed_or_modified_publication_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'a.json').write_text('{}');(p/'publication.json').write_text(json.dumps({'files':{'a.json':'wrong'}}))
   with self.assertRaisesRegex(ValueError,'integrity'):validate_source(p)
if __name__=='__main__':unittest.main()
