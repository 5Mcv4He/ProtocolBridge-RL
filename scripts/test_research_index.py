import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.research_index import build,ROOT
class ResearchIndex(unittest.TestCase):
 def test_real_cohorts_remain_separate(self):
  sources=[ROOT/'experiments/task003-v1/pilot',ROOT/'experiments/task003-v1/repair']
  d=build(sources)['tasks']['axil_to_apb4_queue_003'];self.assertEqual(len(d['cohorts']),2)
  a,b=d['cohorts'];self.assertEqual(sum(g['started'] for g in a['groups'].values()),9);self.assertEqual(sum(g['reward_counts']['one'] for g in a['groups'].values()),1)
  self.assertEqual(sum(g['started'] for g in b['groups'].values()),6);self.assertEqual(sum(g['reward_counts']['zero'] for g in b['groups'].values()),6)
  self.assertEqual(sum(g['tokens'] for g in b['groups'].values()),177257)
  self.assertIsNone(a['api_currency_cost']);self.assertEqual(a['matching_current_task_version'],1)
 def test_duplicate_cohort_refused(self):
  p=ROOT/'experiments/task003-v1/pilot'
  with self.assertRaisesRegex(ValueError,'Duplicate'):build([p,p])
if __name__=='__main__':unittest.main()
