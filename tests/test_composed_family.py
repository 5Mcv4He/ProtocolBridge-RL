import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from task_families.composed_v1.generate import generate,TASK
from task_families.package import verify

class ComposedFamily(unittest.TestCase):
    def test_capsule_contract_and_fail_closed_checker_liveness(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'package';manifest=generate(p)
            self.assertEqual(verify(p),manifest)
            self.assertEqual(manifest['status'],'candidate_not_admitted')
            spec=(p/'tasks'/TASK/'spec.md').read_text()
            self.assertNotIn('no address decoding',spec)
            self.assertIn('unmapped DECERR',spec)
            self.assertIn('tb.sb=sb',(p/'verifier/task003/vip.sv').read_text())
            mechanism=(p/'environment/task003_mechanism.py').read_text()
            for name in re.findall(r'fixtures/task003/[A-Za-z_]+\.sv',mechanism):
                self.assertTrue((p/name).is_file(),name)
            self.assertIn('supports base observation policies only',(p/'environment/policy_experiment.py').read_text())
            obligations=json.loads((p/'tasks'/TASK/'obligations.json').read_text())
            metadata=json.loads((p/'tasks'/TASK/'task.json').read_text())
            controls={Path(x['source']).stem for x in metadata['quality']['negative_controls']}
            for item in obligations:
                self.assertTrue(set(item['controls'])<=controls)
            # A dead checker is a verifier fault even if another observer raises
            # a candidate-looking error. No stimulus or source fingerprint involved.
            script="""from verifier.task003.campaign import interpret
from verifier.task003.scenarios import suite
cases=suite(True)
case=cases[0]
assert {r[1]>>16 for c in cases if c['name'] in ('reset_3','reset_4','reset_5','reset_6','reset_7','reset_8') for r in c['rows']}=={0,1,2}
from verifier.task003.scenarios import REQUIRED_BINS
assert {'x_reset_mapped_0','x_reset_mapped_1','x_reset_mapped_2'}<=REQUIRED_BINS
for missing in ('PBX_ORACLE_OK','PBX_LEDGER_EXECUTED'):
 log='PBX_ORACLE_OK\\nPBX_LEDGER_EXECUTED\\nUVM_ERROR [PB_FUNCTION] mismatch'
 assert interpret(log.replace(missing,''),0,case)['reward'] is None
assert interpret(log,0,case)['reward']==0
"""
            subprocess.run([sys.executable,'-c',script],cwd=p,check=True)
            with self.assertRaises(ValueError):generate(p)

if __name__=='__main__':unittest.main()
