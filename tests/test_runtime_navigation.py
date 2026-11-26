import unittest
from environment.runtime_navigation import observation,valid_start
from environment.runtime_tools import timeline,SIGNALS
class Navigation(unittest.TestCase):
 def record(self):
  pins=[0]*len(SIGNALS);pins[0]=1
  lines=[]
  for c in range(50):
   p=pins[:]
   if c==10:p[1]=p[2]=1
   if c==20:p[11]=p[12]=1
   for phase in (0,1):lines.append('PBR1 %d %d '%(c,phase)+' '.join(format(v,'x') for v in p))
  return {'status':'PASS','source_sha256':'a'*64,'timeline':timeline('\n'.join(lines))}
 def test_success_anchors_activity_not_idle_tail(self):
  r=observation(self.record(),True);self.assertEqual(r['window']['anchor_cycle'],10);self.assertTrue(any('AW' in x['events'] for x in r['rows']))
 def test_event_occurrence_and_absence(self):
  r=observation(self.record(),True,'B:0',8);self.assertEqual(r['window']['anchor_cycle'],20)
  r=observation(self.record(),True,'B:1',8);self.assertEqual(r['window']['status'],'NOT_CAPTURED');self.assertEqual(r['rows'],[])
 def test_reject_non_event_paths_and_bool(self):
  for q in (True,-1,4096,'../../private','secret:0','AW:-1','AW:10000'):
   self.assertFalse(valid_start(q))
   with self.assertRaises(ValueError):observation(self.record(),True,q)
 def test_no_sensitive_field_projection(self):
  r=self.record();r['private']='secret';r['timeline']['samples'][0]['private']='secret'
  self.assertNotIn('secret',str(observation(r,True)));self.assertEqual(observation(r,False),{'status':'PASS'})
