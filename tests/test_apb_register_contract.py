import copy,json,tempfile,unittest
from pathlib import Path
from task_families.apb_register_v1.contract import validate,obligations
from task_families.apb_register_v1.generate import generate,rtl
from task_families.apb_register_v1.verification import update_bytes,scenarios,anchors_sv

C={'task_id':'apb_register_masked_v1','wait_cycles':2,'registers':[
 {'address':12,'reset':0x12345678,'write_mask':0xff00ffff,'access':'rw'},
 {'address':32,'reset':0xffff00ff,'write_mask':0xffffffff,'access':'w1c'},
 {'address':48,'reset':0x55aa9966,'write_mask':0,'access':'ro'}]}

class ContractTests(unittest.TestCase):
 def test_rules_and_interactions(self):
  validate(C);ids={x['id'] for x in obligations(C)}
  self.assertTrue({'W1C_STROBE','RESERVED_BITS','RO_WRITE','IDLE_RESET'}<=ids)
  for key,value in [('wait_cycles',True),('wait_cycles',4)]:
   x=copy.deepcopy(C);x[key]=value
   with self.assertRaises(ValueError):validate(x)
  x=copy.deepcopy(C);x['registers'][1]['reset']=0
  with self.assertRaises(ValueError):validate(x)
  x=copy.deepcopy(C);x['registers'][1]['address']=12
  with self.assertRaises(ValueError):validate(x)
 def test_applicability_not_task_names(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'one';m=generate(C,p);meta=json.loads((p/'task.json').read_text())
   self.assertEqual(len(meta['negative_controls']),8);self.assertFalse(m['industrial_admission'])
   x=copy.deepcopy(C);x['task_id']='apb_register_second_v1';x['wait_cycles']=0
   x['registers']=[dict(r,access='rw',write_mask=0xffffffff) for r in x['registers']]
   q=Path(d)/'two';generate(x,q)
   self.assertEqual(len(json.loads((q/'task.json').read_text())['negative_controls']),4)
   with self.assertRaises(ValueError):generate(C,p)
 def test_references_differ_in_structure(self):
  self.assertIn('bitnum',rtl(C));self.assertNotIn('bitnum',rtl(C,True))
  self.assertNotEqual(rtl(C),rtl(C,fault='ignore_strobe'))

class OracleTests(unittest.TestCase):
 def test_literal_semantic_anchors(self):
  self.assertEqual(update_bytes(0x12345678,0xa1b2c3d4,5,0xffffffff,'rw'),0x12b256d4)
  self.assertEqual(update_bytes(0xffff00ff,0x00ff00ff,5,0xffffffff,'w1c'),0xff000000)
  self.assertEqual(update_bytes(0x12345678,0xffffffff,15,0xff00ffff,'rw'),0xff34ffff)
  self.assertEqual(update_bytes(0x12345678,0xffffffff,15,0,'ro'),0x12345678)
 def test_all_strobe_witnesses_and_reset(self):
  rows=scenarios(C,17,0)
  for r in C['registers']:
   self.assertEqual({x[3] for x in rows if x[0]==1 and x[1]==r['address']},set(range(16)))
  self.assertEqual(sum(x[0]==2 for x in rows),18)
  self.assertEqual(rows,scenarios(C,99,0))
  self.assertIn('PB_ORACLE_ANCHORS_OK',anchors_sv(C))

class ResultTests(unittest.TestCase):
 def test_complete_activity_and_classification(self):
  from task_families.apb_register_v1.results import simulation_result as check
  good='PB_ORACLE_ANCHORS_OK\nPB_REGISTER_ACTIVITY\nPB_REGISTER_DONE checked=80 resets=3 waits=160\nPB_REGISTER_COVERAGE observed=51 required=51\nUVM_ERROR : 0\nUVM_FATAL : 0\n'
  self.assertEqual(check(good,0,80,3,160,3)['reward'],1)
  self.assertIsNone(check(good.replace('checked=80','checked=79'),0,80,3,160,3)['reward'])
  self.assertIsNone(check(good+good,0,80,3,160,3)['reward'])
  self.assertEqual(check('[PB_FUNCTION] mismatch',1,80,3,160,3)['reward'],0)
  self.assertIsNone(check('[PB_FUNCTION] mismatch PB_INFRA broken',1,80,3,160,3)['reward'])
  self.assertIsNone(check('PB_REGISTER_TIMEOUT',0,80,3,160,3)['reward'])
  self.assertEqual(check('PB_REGISTER_ACTIVITY PB_REGISTER_TIMEOUT',0,80,3,160,3)['category'],'test_timeout')
 def test_compile_failure_attribution(self):
  from task_families.apb_register_v1.results import compile_result as check
  self.assertEqual(check('Error-[SE] syntax error\ncandidate.sv, 12',1)['reward'],0)
  self.assertIsNone(check('Error-[SE] syntax error\ntb.sv, 12',1)['reward'])

class SourceBoundaryTests(unittest.TestCase):
 def test_fixed_module_and_no_simulation_side_effects(self):
  from task_families.apb_register_v1.campaign import source_policy
  self.assertIsNone(source_policy(rtl(C)));self.assertIsNone(source_policy(rtl(C,True)))
  for extra in ('initial $display("PASS");','assign prdata=tb.model[0];','`include "private.sv"','initial #10 waits=0;'):
   self.assertIsNotNone(source_policy(rtl(C).replace('endmodule',extra+'\nendmodule')))
  self.assertIsNotNone(source_policy(rtl(C).replace('input logic clk','input logic another_clk')))
