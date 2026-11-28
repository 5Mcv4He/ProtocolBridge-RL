import unittest
from task_families.composed_v2.reset_controls_v3 import corrected


class ResetMutationOrdering(unittest.TestCase):
    def test_only_reset_branch_changes_and_violation_is_last(self):
        ref='''always_ff @(posedge clk) begin
  if(!rst_n) begin
   state<=IDLE;ac<=0;
   s_bvalid<=0;s_rvalid<=0;
   target<=0;paddr<=0;pwdata<=0;pstrb<=0;pwrite<=0;
  end else begin
   if(done) begin s_bvalid<=1;s_rvalid<=1;end
  end
 end'''
        for target in range(3):
            for stage in (7,8):
                new=corrected(ref,target,stage)
                original_tail=ref.split('  end else begin',1)[1]
                self.assertEqual(new.split('  end else begin',1)[1],original_tail)
                reset=new.split('  end else begin',1)[0]
                signal='s_bvalid' if stage==7 else 's_rvalid'
                self.assertGreater(reset.rindex(signal+'<=1'),reset.rindex(signal+'<=0'))
                self.assertIn('target==%d'%target,reset)
                with self.assertRaises(ValueError):corrected(new,target,stage)
        with self.assertRaises(ValueError):corrected(ref,3,7)
        with self.assertRaises(ValueError):corrected(ref,0,3)


if __name__=='__main__':unittest.main()
