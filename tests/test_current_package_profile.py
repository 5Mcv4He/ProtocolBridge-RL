import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from environment.package_backend_v2 import Backend
from environment.package_admission_v3 import validate
from environment.native_tools.run_package_v2 import run
from environment.artifact_task.session_v4 import sha


class CurrentVerifierDomain(unittest.TestCase):
    def test_old_or_wrong_verifier_domain_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / 'family-manifest.json'
            config = root / 'config.json'
            config.write_text('{}')
            obj = Backend.__new__(Backend)
            obj.package = root
            obj.config = config
            obj.config_sha256 = sha(config)
            obj.inputs = {}
            obj.input_sha256 = {}
            current = dict(schema='router-capsule-v1', files={},
                           family='x2p_three_target_router_v5',
                           execution_adapter='router-deployment-v1',
                           qualification_revision=2, verifier_revision='response-ownership-v1')
            for changes in ({}, {'family': 'x2p_three_target_router_v3'},
                            {'verifier_revision': None}, {'qualification_revision': 1}):
                manifest.write_text(json.dumps(dict(current, **changes)))
                obj.manifest_sha256 = sha(manifest)
                if changes:
                    with self.assertRaisesRegex(ValueError, 'Unsupported execution'):
                        obj.check()
                else:
                    obj.check()

    def test_old_admission_does_not_become_current_by_setting_admitted(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = Path(tmp) / 'old.json'
            record.write_text(json.dumps({'schema': 'router-layered-admission-v2', 'admitted': True}))
            with self.assertRaisesRegex(ValueError, 'No admission'):
                validate(record, '/unused')

    def test_old_study_refused_before_any_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = Path(tmp) / 'plan.json'
            plan.write_text(json.dumps({'schema': 'native-router-package-study-v1'}))
            with patch('environment.native_tools.run_package_v2.unchanged', return_value=True), \
                    patch('environment.native_tools.run_package_v2.subprocess.run') as process:
                with self.assertRaisesRegex(ValueError, 'Unsupported study'):
                    run(plan, 'old', Path(tmp) / 'run')
                process.assert_not_called()


if __name__ == '__main__':
    unittest.main()
