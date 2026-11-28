import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from task_families.composed_v2.contract import validate, anchors, reset_bins
from task_families.composed_v2.generate import generate
from task_families.package import verify


CONTRACT = dict(task_id='x2p_composed_shifted_v2', windows=[[0x10004,65536],[0x8004000c,65536],[0x50008,65536]],
                purpose='Non-page-aligned routing identity through retirement-held request queues')


class ComposedWindows(unittest.TestCase):
    def test_domain_and_independent_boundary_anchors(self):
        c=copy.deepcopy(CONTRACT);validate(c)
        rows={a:(t,o) for a,t,o in anchors(c)}
        self.assertEqual(rows[0x20000],(0,65532))
        self.assertEqual(rows[0x20004],(-1,0))
        self.assertEqual(rows[0x8004000c],(1,0))
        c['windows'][1]=c['windows'][0][:]
        with self.assertRaises(ValueError):validate(c)
        c=copy.deepcopy(CONTRACT);c['windows'][0][1]=32768
        with self.assertRaises(ValueError):validate(c)

    def test_generated_composition_has_real_phase_obligations(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'package';m=generate(CONTRACT,out)
            self.assertEqual(verify(out),m)
            self.assertEqual(m['status'],'candidate_not_admitted')
            task=out/'tasks'/CONTRACT['task_id'];meta=json.loads((task/'task.json').read_text())
            self.assertEqual(meta['quality']['required_cross_bins'],66)
            self.assertEqual(len(meta['quality']['negative_controls']),38)
            sb=(out/'verifier/task003/scoreboard.sv').read_text()
            hook=sb[sb.index('observed_reset_phase=0;'):sb.index('    discarded=')]
            self.assertNotIn('reset_stage_active',hook)
            self.assertIn('tb.s_bvalid && !tb.s_bready',hook)
            for row in meta['quality']['negative_controls']:
                self.assertTrue((out/row['source']).is_file())
            script='''from verifier.task003.scenarios import suite,REQUIRED_BINS,WINDOWS
cases=suite(True)
assert len(cases)==42
for target in range(3):
 for stage in range(3,9):
  c=next(c for c in cases if c['name']=='target_reset_t%d_s%d'%(target,stage))
  assert c['reset_stage']==stage
  b,n=WINDOWS[target]
  assert all(b<=r[1]<b+n for r in c['rows']+c['recovery'])
  assert 'x_reset_t%d_s%d'%(target,stage) in REQUIRED_BINS
assert len(REQUIRED_BINS)==66
'''
            subprocess.run([sys.executable,'-c',script],cwd=str(out),check=True)
            self.assertEqual(len(reset_bins()),18)
            with self.assertRaises(ValueError):generate(CONTRACT,out)


if __name__=='__main__':unittest.main()
