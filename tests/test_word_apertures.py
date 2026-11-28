import copy,unittest
from task_families.router_v4.contract import validate,anchors,mask_fault

class WordAperture(unittest.TestCase):
    def contract(self):return {'task_id':'x2p_router_worda_v1','windows':[[0x1004,4100],[0x3008,16],[0x80010000,64]],'purpose':'Sub-page base crosses a global page boundary with a small peer aperture'}
    def test_global_page_carry_uses_local_subtraction(self):
        c=self.contract();validate(c);a={int(x,16):(t,o) for x,t,o in anchors(c)}
        self.assertEqual(a[0x1ffc],(0,0xff8));self.assertEqual(a[0x2000],(0,0xffc));self.assertEqual(a[0x2004],(0,0x1000));self.assertEqual(a[0x2008],(-1,0))
        lane,off=mask_fault(c);base,size=c['windows'][lane];self.assertNotEqual((base+off)&(size-1),off)
    def test_tiny_lane_does_not_require_impossible_local_bit12(self):
        c=self.contract();c['windows'][1]=[0x3008,4];validate(c)
        self.assertNotEqual(mask_fault(c)[0],1)
    def test_alignment_overlap_and_no_carry_rejected(self):
        c=self.contract();c['windows'][0][0]+=1
        with self.assertRaises(ValueError):validate(c)
        c=self.contract();c['windows'][1]=[0x2004,4]
        with self.assertRaises(ValueError):validate(c)
        c=self.contract();c['windows'][0]=[0x1000,8192]
        with self.assertRaises(ValueError):validate(c)

if __name__=='__main__':unittest.main()
