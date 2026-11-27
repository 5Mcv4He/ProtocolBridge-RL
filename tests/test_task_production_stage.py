import json,shutil,tempfile,unittest
from pathlib import Path
from task_families.fifo_checker_v1.qualification import check,ROOT
from scripts.artifact_exchange_v2 import audit
from verifier.status_register.oracle import next_value,TABLES
from verifier.status_register.campaign import interpret_anchor

class ProductionStage(unittest.TestCase):
 def test_generated_checker_package_and_every_file_omission(self):
  for depth in (2,3):
   source=ROOT/'tasks'/('fifo_checker_d%d_v1'%depth)
   self.assertTrue(check(source)['admitted'])
   with tempfile.TemporaryDirectory() as tmp:
    p=Path(tmp)/'task';shutil.copytree(source,p)
    for f in list(p.rglob('*')):
     if not f.is_file():continue
     content=f.read_bytes();f.unlink()
     with self.assertRaises((ValueError,FileNotFoundError)):check(p)
     f.write_bytes(content)
    (p/'extra.txt').write_text('unexpected')
    with self.assertRaises(ValueError):check(p)
 def test_unqualified_depth_refused(self):
  from task_families.fifo_checker_v1.generate_v2 import produce
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'task';produce(5,p)
   with self.assertRaises(ValueError):check(p)
 def test_status_truth_tables_and_cross_lane_anchor(self):
  self.assertEqual(next_value('set_dominant',0x81,1,1,0x42,0xc0),0x43)
  self.assertEqual(next_value('clear_dominant',0x81,1,1,0x42,0xc0),3)
  for mode,table in TABLES.items():
   for b in range(8):
    for (old,hw,clear),expected in table.items():
     self.assertEqual((next_value(mode,old<<b,1,1,hw<<b,clear<<b)>>b)&1,expected)
     self.assertEqual(next_value(mode,old<<b,0,1,255,255),0)
 def test_status_no_vacuous_or_incomplete_pass(self):
  for text,rc in [('',0),('PB_STATUS_COMPLETE rows=9\n',0),('PB_STATUS_COMPLETE rows=10\n',124),('PB_STATUS_INFRA\n',0),('PB_STATUS_COMPLETE rows=10\nPB_STATUS_MISMATCH row=1 expected=0 observed=1\n',0)]:
   self.assertIsNone(interpret_anchor(text,rc,10)['reward'])
  self.assertEqual(interpret_anchor('PB_STATUS_ASYNC row=2\n',0,10)['reward'],0)
  self.assertEqual(interpret_anchor('PB_STATUS_COMPLETE rows=10\n',0,10)['reward'],1)
if __name__=='__main__':unittest.main()
