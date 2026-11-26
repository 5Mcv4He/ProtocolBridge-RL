import copy,json,tempfile,unittest
from pathlib import Path
from environment.runtime_tools import cases,timeline,observation,SIGNALS
from environment.runtime_session import Session,PROFILES
from environment.policy import load
class RuntimeTests(unittest.TestCase):
 def test_request_boundary(self):
  self.assertEqual(cases({'scenario':'write_fifo'})[0]['name'],'write_fifo')
  row=[1,256,123,15,0,0,4,16,0,0]
  self.assertEqual(cases({'transactions':[row]})[0]['rows'],[row])
  for r in [{'scenario':'private'}, {'scenario':'write_fifo','script':'x'},{'transactions':[]},{'transactions':[row]*17},{'transactions':[[True]+row[1:]]},{'transactions':[[1,3]+row[2:]]}]:
   with self.assertRaises(ValueError):cases(r)
 def test_pin_ledger_and_projection(self):
  p=[0]*len(SIGNALS);p[0]=1;p[1]=p[2]=p[4]=p[5]=1
  def line(c,phase):return 'PBR1 %d %d '%(c,phase)+' '.join(format(v,'x') for v in p)+'\n'
  log=line(1,0)+line(1,1)+line(2,0)+'PBQ_ERROR Request capacity exceeded\n'
  t=timeline(log);self.assertEqual(t['samples'][1]['unretired'],[1,1,0]);self.assertEqual(t['samples'][2]['unretired'],[2,2,0])
  t['samples'][0]['secret']='SECRET';t['first_error']['secret']='SECRET'
  r={'status':'FAIL','source_sha256':'a'*64,'timeline':t,'private':'SECRET','invariant':{'code':'Q_CAPACITY','message':'SECRET'}}
  self.assertEqual(observation(r,False),{'status':'FAIL'})
  self.assertNotIn('SECRET',json.dumps(observation(r,True)))
  self.assertEqual(timeline(line(1,0)+'UVM_ERROR : 0\n')['first_error'],None)
  late=timeline(line(1,0)+'PBR_LIMIT\nPBQ_ERROR late\n')
  self.assertTrue(late['truncated']);self.assertIsNone(late['first_error'])
  with self.assertRaises(ValueError):timeline('PBR1 malformed')
 def test_permissions_and_budgets(self):
  for cap in PROFILES:
   with tempfile.TemporaryDirectory() as d:
    w=Path(d)/'work';w.mkdir();(w/'spec.md').write_text('spec');(w/'bridge.sv').write_text('module bridge; endmodule')
    calls=[]
    def backend(*args):calls.append(args);return {'status':'ENV_ERROR','private':'SECRET'}
    s=Session(load('test_diagnostic'),w,Path(d)/'out',[],capability=cap,experimenter=backend)
    a={'tool':'experiment','scenario':'write_fifo'}
    self.assertEqual(s.handle(a)['status'],'REJECTED');self.assertFalse(calls)
    for name in ('spec.md','bridge.sv'):s.handle({'tool':'read','file':name})
    self.assertEqual(s.handle(dict(a,script='SECRET'))['status'],'REJECTED');self.assertFalse(calls)
    for i in range(3):self.assertNotIn('SECRET',json.dumps(s.handle(a)))
    self.assertEqual(s.handle(a)['reason'],'experiment_budget_exhausted');self.assertEqual(len(calls),3)
    for i in range(4):self.assertEqual(s.handle({'tool':'observe','start':0,'count':1})['status'],'ENV_ERROR')
    self.assertEqual(s.handle({'tool':'observe','start':0,'count':1})['reason'],'observe_budget_exhausted')
    self.assertEqual(s.handle({'tool':'read','file':'../private.json'})['status'],'REJECTED')
    self.assertEqual(s.handle({'tool':'submit'})['status'],'SUBMITTED')
    self.assertEqual(s.handle(a)['reason'],'episode_closed')
