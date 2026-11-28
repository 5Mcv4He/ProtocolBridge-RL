import ast
import subprocess
import unittest
from pathlib import Path
from task_families.router_v3.materialize import adapt

ROOT=Path(__file__).resolve().parents[1]

class ExecutionAdapter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=subprocess.check_output(['git','show','194ffbe181601e4876035a35bfa49e7242317d41:verifier/task002/campaign.py'],cwd=str(ROOT)).decode()
        cls.changed=adapt(cls.source)

    def test_reward_and_source_policy_ast_unchanged(self):
        def functions(text):
            return {n.name:ast.dump(n) for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)}
        before,after=functions(self.source),functions(self.changed)
        for name in ('interpret','source_policy','sha'):
            self.assertEqual(before[name],after[name])

    def test_explicit_environment_on_every_execution(self):
        self.assertNotIn('source ~/.bashrc',self.changed)
        self.assertIn("source '+shlex.quote(entry)+' || exit 125",self.changed)
        self.assertIn("inputs['environment_entry']",self.changed)
        self.assertIn("inputs['build_configuration']",self.changed)
        self.assertIn("inputs['campaign']",self.changed)

    def test_unsupported_source_refuses_adaptation(self):
        with self.assertRaises(ValueError):
            adapt(self.source.replace('def shell(command,timeout):','def shell(command,timeout,changed=True):'))

    def test_each_simulation_has_distinct_runtime(self):
        self.assertIn("remote=cfg['remote_root']+'/'+uuid.uuid4().hex",self.changed)
        self.assertIn("copy([directory/'vectors.txt'],remote)",self.changed)
        self.assertIn("if prior['inputs']!=inputs",self.changed)
        self.assertIn("'cp -as '+assets",self.changed)
        self.assertIn('timeout 600 ./simv',self.changed)

if __name__=='__main__':unittest.main()
