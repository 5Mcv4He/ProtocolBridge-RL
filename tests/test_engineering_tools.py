import copy,json,tempfile,unittest
from pathlib import Path
from environment.engineering_tools import compiler_projection,inspect_public
from environment.engineering_session import Session
from environment.policy import load
class Tools(unittest.TestCase):
 def test_compiler(self):
  log='Error-[SE] Syntax error\n  "bridge.sv", 12: token is secret\n private/vector/file API_SECRET'
  x=compiler_projection(log,255)
  self.assertEqual(x['status'],'FAIL');self.assertEqual(x['diagnostics'][0]['line'],12)
  self.assertNotIn('secret',json.dumps(x));self.assertNotIn('private',json.dumps(x))
  for rc,log in [(124,log),(255,log+' LICENSING'),(255,'Error-[SE] "private.sv", 2'),(255,'crash')]:self.assertEqual(compiler_projection(log,rc)['status'],'ENV_ERROR')
 def test_projector_leak(self):
  r={'reward':0,'failed_case':'read_fifo','cases':[{'name':'read_fifo','failures':['Request capacity exceeded','SECRET'] }], 'secret':'private'}
  x=inspect_public(r);self.assertEqual(x['invariant']['code'],'Q_CAPACITY');self.assertNotIn('SECRET',json.dumps(x));self.assertNotIn('private',json.dumps(x))
  r['cases'][0]['failures']=['Request capacity exceeded SECRET'];self.assertIsNone(inspect_public(r)['invariant'])
  r['failed_case']='SECRET';self.assertIsNone(inspect_public(r)['case'])
  r['reward']=None;self.assertEqual(inspect_public(r),{'status':'ENV_ERROR','invariant':None})
 def test_session_budgets(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);w=root/'work';w.mkdir();(w/'spec.md').write_text('spec');(w/'bridge.sv').write_text('module bridge; endmodule')
   calls=[]
   def compiler(*a):calls.append(a);return {'status':'PASS'}
   s=Session(load('test_diagnostic'),w,root/'out',[],compiler=compiler)
   self.assertEqual(s.handle({'tool':'compile'})['status'],'REJECTED');self.assertFalse(calls)
   for f in ('spec.md','bridge.sv'):s.handle({'tool':'read','file':f})
   self.assertEqual(s.handle({'tool':'inspect'})['reason'],'no_public_result')
   self.assertEqual(s.handle({'tool':'compile','command':'x'})['status'],'REJECTED')
   for _ in range(2):self.assertEqual(s.handle({'tool':'compile'})['status'],'PASS')
   self.assertEqual(s.handle({'tool':'compile'})['reason'],'compile_budget_exhausted');self.assertEqual(len(calls),2)
   s.public=[{'action':4,'source_sha256':'a'*64,'result':{'reward':1}}]
   for _ in range(2):self.assertEqual(s.handle({'tool':'inspect'})['status'],'PASS')
   self.assertEqual(s.handle({'tool':'inspect'})['reason'],'inspect_budget_exhausted')
   self.assertEqual(s.handle({'tool':'read','file':'verifier/source.sv'})['status'],'REJECTED')
   self.assertEqual(s.handle({'tool':'submit'})['status'],'SUBMITTED')
   self.assertEqual(s.handle({'tool':'compile'})['reason'],'episode_closed');self.assertEqual(len(calls),2)
if __name__=='__main__':unittest.main()
