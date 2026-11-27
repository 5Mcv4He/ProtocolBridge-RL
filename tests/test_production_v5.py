import json,tempfile,unittest
from pathlib import Path
from verification_resources import production_v5 as producer

class CurrentMaterialization(unittest.TestCase):
 def test_current_families_reset_and_strict_dependencies(self):
  families=('fifo-checker-expanded','rffe-register','bitfold-synthesis','i2c-completion')
  with tempfile.TemporaryDirectory() as tmp:
   for family in families:
    for variant,task in producer.FAMILIES[family].items():
     p=Path(tmp)/task;m=producer.materialize(family,variant,p)
     self.assertEqual(producer.reset(p,Path(tmp)/(task+'-work'))['task_id'],task)
     self.assertIn('environment/artifact_task/session_v4.py',m['source_dependencies'])
     for key in m['source_dependencies']:
      changed=dict(m,source_dependencies={k:v for k,v in m['source_dependencies'].items() if k!=key})
      (p/'manifest.json').write_text(json.dumps(changed))
      with self.assertRaises(ValueError):producer.check(p)
     (p/'manifest.json').write_text(json.dumps(m))
     for f in list((p/'task').rglob('*')):
      if not f.is_file():continue
      data=f.read_bytes();f.unlink()
      with self.assertRaises((ValueError,FileNotFoundError)):producer.check(p)
      f.write_bytes(data)
     (p/'extra.txt').write_text('unexpected')
     with self.assertRaises(ValueError):producer.check(p)

if __name__=='__main__':unittest.main()
