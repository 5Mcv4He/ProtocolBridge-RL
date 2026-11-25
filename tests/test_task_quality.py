"""Admission integrity and projections; real EDA gate evidence is separate."""
import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from environment.task_quality import validate_manifest,require_admission
from environment.control_bank import bundle
from environment.policy import load
from environment.task002 import project,reset
from verifier.task002.scenarios import suite,target,BASES
ROOT=Path(__file__).resolve().parents[1]
class QualityContract(unittest.TestCase):
 def setUp(self):self.m=json.loads((ROOT/'tasks/axil_to_apb4_router_002/task.json').read_text())
 def test_valid_manifest(self):validate_manifest(self.m,suite())
 def test_duplicate_controls_rejected(self):
  self.m['quality']['negative_controls']=[self.m['quality']['negative_controls'][0]]*13
  with self.assertRaisesRegex(ValueError,'Duplicate'):validate_manifest(self.m,suite())
 def test_missing_requirement_rejected(self):
  self.m['quality']['required_requirements'].append('NONEXISTENT')
  with self.assertRaisesRegex(ValueError,'Missing requirements'):validate_manifest(self.m,suite())
 def test_duplicate_cases_rejected(self):
  with self.assertRaisesRegex(ValueError,'Duplicate'):validate_manifest(self.m,suite()+suite()[:1])
 def test_too_few_controls_rejected(self):
  self.m['quality']['negative_controls']=self.m['quality']['negative_controls'][:1]
  with self.assertRaisesRegex(ValueError,'Insufficient'):validate_manifest(self.m,suite())
 def test_failed_admission_cannot_launch(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'result.json').write_text('{"accepted":false}');(p/'freeze.json').write_text('{}')
   with self.assertRaisesRegex(ValueError,'not admitted'):require_admission(ROOT/'tasks/axil_to_apb4_router_002',p)
 def test_unadmitted_task_fails_before_credentials(self):
  from environment.policy_experiment import experiment
  with self.assertRaisesRegex(ValueError,'admission'):experiment('/nonexistent-unused',['spec_only'],'test',1,task_id='axil_to_apb4_router_002')
 def test_every_high_alias_bit(self):
  c=next(c for c in suite(True) if c['name']=='decode_misses');addresses={r[1] for r in c['rows']}
  for base in BASES:
   for bit in range(12,32):
    a=base^(1<<bit)
    if target(a)<0:self.assertIn(a,addresses)
 def test_reset_is_fresh_and_complete(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'work';r=reset(p);self.assertEqual(r['task'],self.m['task_id'])
   self.assertEqual((p/'bridge.sv').read_bytes(),(ROOT/'tasks'/self.m['task_id']/self.m['initial_rtl']).read_bytes())
   with self.assertRaises(FileExistsError):reset(p)
 def test_control_bank_rejects_port_mismatch(self):
  with tempfile.TemporaryDirectory() as d:
   a=Path(d)/'a.sv';b=Path(d)/'b.sv'
   a.write_text('module bridge(input logic a,output logic b);assign b=a;endmodule')
   b.write_text('module bridge(input logic x,output logic b);assign b=x;endmodule')
   with self.assertRaises(ValueError):bundle([a,b])
class RouterFeedback(unittest.TestCase):
 def test_white_list_and_no_sensitive_data(self):
  r={'reward':0,'category':'transaction_functional_error','failed_case':'decode_misses','secret':'SENSITIVE','cases':[{'name':'decode_misses','failures':['SENSITIVE']}],'path':'SENSITIVE'}
  for mode in ['test_verdict','test_diagnostic']:
   o=project(r,load(mode),1);self.assertNotIn('SENSITIVE',json.dumps(o))
   expected={'status','remaining_test_calls'}
   if mode=='test_diagnostic':expected|={'category','first_failed_case','diagnostic'};self.assertEqual(o['first_failed_case'],'decode_misses')
   self.assertEqual(set(o),expected)
 def test_unknown_case_and_exception_not_echoed(self):
  r={'reward':None,'category':'UNTRUSTED_SECRET','failed_case':'SECRET','reason':'SECRET'}
  o=project(r,load('test_diagnostic'),1)
  self.assertEqual(o['status'],'ENV_ERROR');self.assertEqual(o['category'],'infrastructure_error');self.assertIsNone(o['first_failed_case']);self.assertNotIn('SECRET',json.dumps(o))
 def test_valid_edit_budget_and_submission(self):
  from environment.task002 import Session
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);reset(root/'work');s=Session(load('spec_only'),root/'work',root/'out',suite())
   for f in ['spec.md','bridge.sv']:s.handle({'tool':'read','file':f})
   source=(ROOT/'fixtures/task002/reference.sv').read_text()
   self.assertEqual(s.handle({'tool':'edit','content':source})['status'],'EDITED')
   self.assertEqual(s.handle({'tool':'test'})['status'],'REJECTED');self.assertEqual(s.tests,0)
   self.assertEqual(s.handle({'tool':'submit'})['status'],'SUBMITTED')
   self.assertEqual((root/'out/submission/bridge.sv').read_text(),source)
if __name__=='__main__':unittest.main()
