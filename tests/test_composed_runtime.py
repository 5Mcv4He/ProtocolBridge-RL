import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from environment.composed_backend_v1 import Backend, sha
from environment.composed_inputs_v1 import seeds_checked
from environment.composed_admission_v1 import source_match
from environment.native_tools.run_composed_v1 import unchanged


class ComposedRuntime(unittest.TestCase):
    def test_seed_identity_and_bounds(self):
        good=dict(public=17,terminal=401,heldout=809)
        self.assertEqual(seeds_checked(good),good)
        for bad in ({},dict(good,heldout=401),dict(good,public=True),dict(good,heldout=2**31)):
            with self.assertRaises(ValueError):seeds_checked(bad)

    def test_complete_role_inputs_required_before_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            b=Backend.__new__(Backend);b.package=Path(tmp);b.check=lambda:None
            b.seeds=dict(public=17,terminal=401,heldout=809)
            expected={r:[{'case':r,'value':n} for n in range(2)] for r in b.seeds}
            b.inputs={r:b.package/(r+'.json') for r in expected}
            for r,p in b.inputs.items():p.write_text(json.dumps(expected[r]))
            with patch('environment.composed_backend_v1.subprocess.run',return_value=SimpleNamespace(returncode=0,stdout=json.dumps(expected).encode())):
                b.validate_complete_inputs()
                b.inputs['public'].write_text(json.dumps(expected['public'][:1]))
                with self.assertRaisesRegex(ValueError,'complete frozen public'):b.validate_complete_inputs()
                b.inputs['public'].write_text(json.dumps(expected['terminal']))
                with self.assertRaises(ValueError):b.validate_complete_inputs()

    def test_domain_cache_and_changed_dependencies(self):
        with tempfile.TemporaryDirectory() as tmp:
            b=Backend.__new__(Backend);b.package=Path(tmp);b.config=Path(tmp)/'config.json'
            m=Path(tmp)/'family-manifest.json';m.write_text('{}');b.manifest_sha256=sha(m)
            b.config.write_text('{}');b.config_sha256=sha(b.config);b.inputs={};b.input_sha256={}
            domain=dict(family='routed_retirement_windows_v2',execution_adapter='composed-source-environment-v1',control_revision='reset-last-assignment-v1')
            with patch('environment.composed_backend_v1.verify',return_value=domain):
                b.check()
                for field,value in [('variant',0),('compile_cache','cache')]:
                    b.config.write_text(json.dumps({field:value}));b.config_sha256=sha(b.config)
                    with self.assertRaises(ValueError):b.check()
                b.config.write_text('{}');b.config_sha256=sha(b.config)
                m.write_text('{"changed":true}')
                with self.assertRaises(ValueError):b.check()
            m.write_text('{}')
            with patch('environment.composed_backend_v1.verify',return_value=dict(domain,family='unqualified')):
                with self.assertRaises(ValueError):b.check()

    def test_reused_mechanism_requires_complete_dependencies(self):
        with self.assertRaises(ValueError):source_match({},['environment/package_session.py'])
        self.assertFalse(unchanged({'source_files':{}}))

    def test_existing_grade_and_unknown_role_never_execute(self):
        with tempfile.TemporaryDirectory() as tmp:
            b=Backend.__new__(Backend);b.inputs={'public':'unused'};b.check=lambda:None
            source=Path(tmp)/'candidate.sv';source.write_text('module bridge; endmodule')
            out=Path(tmp)/'run';out.mkdir()
            with patch('environment.composed_backend_v1.subprocess.run',side_effect=AssertionError('No subprocess')):
                with self.assertRaises(ValueError):b.grade(source,out,'public')
                with self.assertRaises(ValueError):b.grade(source,Path(tmp)/'other','private')


if __name__=='__main__':unittest.main()
