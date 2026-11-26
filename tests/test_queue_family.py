import json,tempfile,unittest
from pathlib import Path
from task_families.queue_v1.generate import generate,obligations,HERE
from task_families.package import verify
class QueueFamily(unittest.TestCase):
 def test_bounded_contracts_and_obligations(self):
  c=json.loads((HERE/'contracts.json').read_text())['instances']
  self.assertEqual([(x['write_capacity'],x['read_capacity']) for x in c],[(1,1),(3,3),(1,3)])
  for x in c:
   o=obligations(x);self.assertEqual(len(o),3);self.assertTrue(all(a['stimulus'] and a['oracle'] and a['coverage'] and a['controls'] for a in o))
  with tempfile.TemporaryDirectory() as d:
   bad=dict(c[0],write_capacity=4)
   with self.assertRaises(ValueError):generate(bad,Path(d)/'invalid')
 def test_complete_package_and_integrity(self):
  c=json.loads((HERE/'contracts.json').read_text())['instances'][1]
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'package';m=generate(c,p);self.assertEqual(verify(p),m)
   self.assertLess(len(m['files']),400)
   self.assertIn('capacity_aw=3',(p/'verifier/task003/scoreboard.sv').read_text())
   self.assertIn('family_check();',(p/'verifier/task003/tb.sv').read_text())
   self.assertIn('runtime-events-v2',(p/'environment/runtime_session.py').read_text())
   (p/'environment/runtime_navigation.py').write_text('changed')
   with self.assertRaises(ValueError):verify(p)
