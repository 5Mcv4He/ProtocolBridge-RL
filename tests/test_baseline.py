"""The release gate must reject drift; these checks do not run EDA simulation."""
import json,shutil,tempfile,unittest
from pathlib import Path
from environment.check_baseline import check
from environment.reset import ROOT

class StandardBaseline(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        manifest='tasks/axil_to_apb4_001/baseline.json'
        m=json.loads((ROOT/manifest).read_text())
        for name in [manifest]+list(m['runtime_files'])+list(m['evidence_files']):
            dest=self.root/name;dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/name,dest)
    def test_saved_baseline_passes_without_claiming_simulation(self):
        r=check(self.root)
        self.assertEqual(r['status'],'pass');self.assertFalse(r['simulation_executed'])
    def test_changed_reference_is_rejected(self):
        p=self.root/'fixtures/reference.sv';p.write_text(p.read_text()+'\n// drift\n')
        self.assertEqual(check(self.root)['status'],'fail')
    def test_retired_backend_is_rejected(self):
        (self.root/'verifier/v2').mkdir()
        self.assertEqual(check(self.root)['status'],'fail')
    def test_altered_agent_evidence_is_rejected(self):
        p=self.root/'experiments/industrial-v3/agent/result.json';r=json.loads(p.read_text());r['reward']=0
        p.write_text(json.dumps(r))
        self.assertEqual(check(self.root)['status'],'fail')

if __name__=='__main__':unittest.main()
