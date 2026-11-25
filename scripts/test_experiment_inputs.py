import hashlib,json,tempfile,unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from verify_experiment_inputs import frozen_inputs
class FrozenInputs(unittest.TestCase):
 def test_hashes_must_match_before_simulation(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);data='[{"rows": [[1,2,3]]}]';h=hashlib.sha256(data.encode()).hexdigest()
   (root/'experiment.json').write_text(json.dumps({'paired_suite_hashes':{'1':{'reward':h,'evaluation':h}}}))
   for suffix in ('submission/grade/cases.json','reserved-evaluation/cases.json'):
    p=root/'r01-spec_only'/suffix;p.parent.mkdir(parents=True);p.write_text(data)
   m,items=frozen_inputs(root);self.assertEqual(len(items),2);self.assertTrue(all(x['sha256']==h for x in items))
   (root/'r01-spec_only/submission/grade/cases.json').write_text('[]')
   with self.assertRaisesRegex(ValueError,'Missing exact'):frozen_inputs(root)
if __name__=='__main__':unittest.main()
