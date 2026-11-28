import copy,unittest
from task_families.router_v2.contract import anchors,validate_domain,obligations
class Domain(unittest.TestCase):
 def c(self):return dict(task_id='x2p_router_spacea_v1',windows=[[4096,8192],[12288,4096],[1073741824,12288]],purpose='adjacent with high irregular window')
 def test_anchor_boundary_and_carry(self):
  a={int(x,16):(lane,off) for x,lane,off in anchors(self.c())}
  self.assertEqual(a[12284],(0,8188));self.assertEqual(a[12288],(1,0));self.assertEqual(a[8192],(0,4096));self.assertEqual(a[0],(-1,0))
 def test_inapplicable_negative_rejected(self):
  c=self.c();c['windows']=[[4096,4096],[12288,4096],[1073741824,4096]]
  with self.assertRaises(ValueError):validate_domain(c)
 def test_alias_witness_must_be_unmapped(self):
  c=self.c();c['windows'][2]=[2147487744,12288]
  with self.assertRaises(ValueError):validate_domain(c)
 def test_overlap_rejected(self):
  c=self.c();c['windows'][1][0]=8192
  with self.assertRaises(ValueError):validate_domain(c)
 def test_obligations_not_admission(self):
  o=obligations(self.c());self.assertEqual(o['adjacent_pairs'],[[0,1]]);self.assertEqual(o['non_power_two_targets'],[2]);self.assertIn('require industrial evidence',o['status'])
if __name__=='__main__':unittest.main()
