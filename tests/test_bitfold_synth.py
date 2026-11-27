import tempfile,unittest
from pathlib import Path
from task_families.bitfold_synth_v1.generate import generate,rtl,initial,controls
from verifier.bitfold_synth.oracle import value,corpus
from verifier.bitfold_synth.campaign import source_policy
from verifier.bitfold_synth.results import synthesis,simulation

class BitfoldTests(unittest.TestCase):
 def test_independent_semantics(self):
  for x in range(256):
   self.assertEqual(value('population',x),sum((x>>i)&1 for i in range(8)))
   expected=8 if not x else next(i for i in range(8) if x&(1<<i))
   self.assertEqual(value('trailing_zero',x),expected)
 def test_all_inputs_three_predecessor_orders(self):
  phases=[]
  for p in ('public','terminal','evaluation'):
   rows=corpus('population',p);self.assertEqual(len(rows),768)
   for start in (0,256,512):self.assertEqual({x for x,y in rows[start:start+256]},set(range(256)))
   phases.append(rows)
  self.assertNotEqual(phases[0],phases[1]);self.assertNotEqual(phases[1],phases[2])
 def test_generated_interfaces(self):
  for m in ('population','trailing_zero'):
   for s in [rtl(m),rtl(m,True),initial(m)]+list(controls(m).values()):self.assertIsNone(source_policy(s))
   self.assertIsNotNone(source_policy(rtl(m).replace('[3:0]','[7:0]')))
   with tempfile.TemporaryDirectory() as t:generate(m,Path(t)/'task')
 def test_fail_closed(self):
  good=''.join('PB_%s=1\n'%k for k in ('ANALYZE','ELABORATE','LINK','DESIGN','COMPILE','WRITE','DONE'))+'PB_REGISTERS=0\nPB_UNMAPPED=0\n'
  self.assertEqual(synthesis(good,0)['reward'],1)
  self.assertIsNone(synthesis(good.replace('PB_DONE=1',''),0)['reward'])
  self.assertEqual(synthesis(good.replace('PB_REGISTERS=0','PB_REGISTERS=1'),0)['reward'],0)
  self.assertEqual(synthesis('PB_ANALYZE=1\nError: Loop exceeded (ELAB-900)\nPB_ELABORATE=0\n',0)['category'],'synthesis_error')
  self.assertIsNone(synthesis('Error: license unavailable DCSH-1\n',0)['reward'])
  self.assertIsNone(simulation('',0,768)['reward'])
  self.assertEqual(simulation('PB_BITFOLD_MISMATCH row=1\n',0,768)['reward'],0)

if __name__=='__main__':unittest.main()
