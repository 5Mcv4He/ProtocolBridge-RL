"""Catalog/dispatch acceptance; no license or model required."""
import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tasks import load_catalog,execute,quality_command,rollout_command,ROOT
class Catalog(unittest.TestCase):
 def setUp(self):self.catalog=load_catalog()
 def test_four_distinct_contracts(self):
  self.assertEqual(len(self.catalog),4)
  self.assertEqual(len({t['spec'] for t in self.catalog.values()}),4)
 def test_real_resets_and_wrong_task_guard(self):
  with tempfile.TemporaryDirectory() as d:
   for name,t in self.catalog.items():
    w=Path(d)/name;execute('reset',t,w)
    self.assertEqual((w/'bridge.sv').read_bytes(),(ROOT/t['initial_rtl']).read_bytes())
    self.assertEqual((w/'spec.md').read_bytes(),(ROOT/t['spec']).read_bytes())
    with self.assertRaises(FileExistsError):execute('reset',t,w)
   with self.assertRaisesRegex(ValueError,'Spec'):execute('test',self.catalog['axil_to_apb4_001'],Path(d)/'axil_to_apb4_queue_003',Path(d)/'unused')
 def test_invalid_catalog_rejected(self):
  data={'schema_version':1,'tasks':list(self.catalog.values())}
  for mutation in ('duplicate','path','version','extra'):
   x=copy.deepcopy(data)
   if mutation=='duplicate':x['tasks'].append(x['tasks'][0])
   if mutation=='path':x['tasks'][1]['spec']='../private/spec.md'
   if mutation=='version':x['tasks'][1]['version']=999
   if mutation=='extra':x['tasks'][1]['unknown']='broaden permissions'
   with tempfile.TemporaryDirectory() as d:
    p=Path(d)/'catalog.json';p.write_text(json.dumps(x))
    with self.assertRaises(ValueError):load_catalog(p)
 def test_dispatch_keeps_gate_and_task(self):
  t=self.catalog['axil_to_apb4_queue_003'];c=quality_command(t,'out');self.assertIn('environment.task_quality',c)
  c=rollout_command(t,['--out','out','--admission','gate']);self.assertEqual(c[c.index('--task')+1],t['task_id']);self.assertIn('--admission',c)
  with self.assertRaises(ValueError):rollout_command(t,['--task=axil_to_apb4_001'])
 def test_legacy_path_preserved(self):
  t=self.catalog['axil_to_apb4_001'];self.assertIn('environment.validate_v3',quality_command(t,'out'))
  with self.assertRaises(ValueError):quality_command(t,'out',True)
if __name__=='__main__':unittest.main()
