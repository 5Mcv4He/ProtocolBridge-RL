import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from environment.register_backend_v1 import Backend, sha
from environment.register_inputs_v1 import write, derive
from task_families.apb_register_v1.generate import generate
from environment.native_tools.run_register_v1 import environment_digest

C = {'task_id': 'apb_register_runtimeunit_v1', 'wait_cycles': 1, 'registers': [
    {'address': 0, 'reset': 0x12345678, 'write_mask': 0xffffffff, 'access': 'rw'},
    {'address': 12, 'reset': 0xffff00ff, 'write_mask': 0xffffffff, 'access': 'w1c'}]}
SEEDS = {'public': 1, 'terminal': 2, 'heldout': 3}


class RuntimeTests(unittest.TestCase):
    def test_environment_digest_ignores_setup_messages_not_identity(self):
        h='a'*64
        self.assertEqual(environment_digest('setup status\n'+h+'  /example/env.sh\n','/example/env.sh'),h)
        for output in (h+'  /other.sh\n',(h+'  /example/env.sh\n')*2,'no digest'):
            with self.assertRaises(ValueError):environment_digest(output,'/example/env.sh')

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.package = self.root/'materials'
        generate(C, self.package)
        self.inputs = write(C, SEEDS, self.root/'inputs')
        self.config = self.root/'config.json'
        self.cfg = dict(host='example', ssh_config='/unavailable/ssh', remote_root='/unavailable/jobs',
                        eda_env_script='/unavailable/env.sh', apb_vip_root='/unavailable/vip',
                        environment_entry_sha256='0'*64, toolchain={})
        self.config.write_text(json.dumps(self.cfg))

    def tearDown(self):
        self.tmp.cleanup()

    def backend(self, **kw):
        args = dict(package=self.package, manifest_sha256=sha(self.package/'manifest.json'),
                    config=self.config, inputs=self.inputs, seeds=SEEDS)
        args.update(kw)
        return Backend(**args)

    def test_three_roles_have_complete_activity(self):
        d = derive(C, SEEDS)
        self.assertEqual(d['public']['random_count'], 12)
        self.assertEqual(d['terminal']['random_count'], 24)
        self.assertNotEqual(d['terminal']['vectors'], d['heldout']['vectors'])
        for role in d:
            self.assertGreater(len(d[role]['vectors']), 100)

    def test_input_omission_and_role_alias_rejected(self):
        alias = dict(self.inputs, heldout=self.inputs['terminal'])
        with self.assertRaises(ValueError):
            self.backend(inputs=alias)
        p = Path(self.inputs['public'])
        data = json.loads(p.read_text())
        data['vectors'].pop()
        p.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'Complete frozen input'):
            self.backend()

    def test_seed_bounds_and_uniqueness(self):
        for seeds in ({'public': 1, 'terminal': 1, 'heldout': 2},
                      dict(SEEDS, heldout=True), dict(SEEDS, terminal=-1), {'public': 1}):
            with self.assertRaises(ValueError):
                derive(C, seeds)

    def test_changed_inputs_and_config_fail_before_execution(self):
        b = self.backend()
        with patch.object(b, 'remote', side_effect=AssertionError('No remote work')):
            self.config.write_text(json.dumps(dict(self.cfg, host='changed')))
            with self.assertRaisesRegex(ValueError, 'Configuration changed'):
                b.grade(self.package/'fixtures/reference.sv', self.root/'out', 'public')

    def test_invalid_source_is_not_executed(self):
        b = self.backend()
        src = self.root/'bad.sv'
        src.write_text('module bridge; initial $finish; endmodule')
        with patch.object(b, 'remote', side_effect=AssertionError('No remote work')):
            r = b.grade(src, self.root/'out', 'public')
        self.assertIsNone(r['reward'])
        self.assertEqual(r['category'], 'invalid_submission')
        self.assertFalse((self.root/'out/deployment.json').exists())

    def test_reject_cache_and_variant_authority(self):
        for field, value in [('variant', 0), ('compile_cache', '/other')]:
            self.config.write_text(json.dumps(dict(self.cfg, **{field: value})))
            with self.assertRaises(ValueError):
                self.backend()

    def test_never_overwrite_existing_grade(self):
        b = self.backend()
        out = self.root/'out'
        out.mkdir()
        with patch.object(b, 'remote', side_effect=AssertionError('No remote work')):
            with self.assertRaises(FileExistsError):
                b.grade(self.package/'fixtures/reference.sv', out, 'public')


if __name__ == '__main__':
    unittest.main()
