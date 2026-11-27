import json
import tempfile
import unittest
from pathlib import Path
from verification_resources import production_v2 as producer
from verification_resources.dependencies import local_import_closure


class RequiredDependencies(unittest.TestCase):
    def test_all_required_entries_are_mandatory(self):
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp) / 'package'
            original = producer.materialize('reference-repair', 'wrap', package)
            self.assertIn('environment/artifact_task/runner_v6.py', original['source_dependencies'])
            self.assertIn('environment/artifact_task/session_v2.py', original['source_dependencies'])
            self.assertIn('verifier/independent_formal/anchor.py', original['source_dependencies'])
            for key in original['source_dependencies']:
                with self.subTest(omitted=key):
                    changed = json.loads(json.dumps(original))
                    del changed['source_dependencies'][key]
                    (package / 'manifest.json').write_text(json.dumps(changed))
                    with self.assertRaises(ValueError):
                        producer.check(package)

    def test_identity_content_and_extra_files_reject_before_reset(self):
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp) / 'package'
            original = producer.materialize('reference-repair', 'saturating', package)
            for field in ('producer_sha256', 'runtime', 'task_id', 'schema'):
                changed = dict(original, **{field: 'substituted'})
                (package / 'manifest.json').write_text(json.dumps(changed))
                with self.assertRaises(ValueError):
                    producer.reset(package, Path(tmp) / 'work')
                self.assertFalse((Path(tmp) / 'work').exists())
            (package / 'manifest.json').write_text(json.dumps(original))
            (package / 'unexpected.py').write_text('print("not part of task")')
            with self.assertRaises(ValueError):
                producer.check(package)

    def test_actual_materialization_check_reset(self):
        with tempfile.TemporaryDirectory() as tmp:
            for family, variants in producer.FAMILIES.items():
                for variant, task in variants.items():
                    p = Path(tmp) / task
                    producer.materialize(family, variant, p)
                    result = producer.reset(p, Path(tmp) / (task + '-work'))
                    self.assertEqual(result, {'task_id': task, 'initialized': True})

    def test_relative_and_package_imports_followed(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / 'pkg').mkdir()
            for name, text in {'pkg/__init__.py': '', 'pkg/main.py': 'from . import sibling\nimport json',
                               'pkg/sibling.py': 'from pkg.helper import value',
                               'pkg/helper.py': 'value=1'}.items():
                (p / name).write_text(text)
            self.assertEqual(set(local_import_closure(p, ['pkg/main.py'])),
                             {'pkg/__init__.py', 'pkg/main.py', 'pkg/sibling.py', 'pkg/helper.py'})


if __name__ == '__main__':
    unittest.main()
