import unittest
from environment.package_admission import source_match,NATIVE_FILES,BACKEND_FILES,sha,ROOT
from environment.native_tools.run_package import required_sources,unchanged

class QualificationBinding(unittest.TestCase):
    def test_missing_dependency_and_stale_hash_rejected(self):
        files=set(NATIVE_FILES+BACKEND_FILES);rows={f:sha(ROOT/f) for f in files}
        self.assertEqual(source_match(rows,files),rows)
        bad=dict(rows);bad.pop(next(iter(bad)))
        with self.assertRaises(ValueError):source_match(bad,files)
        bad=dict(rows);bad[next(iter(bad))]='0'*64
        with self.assertRaises(ValueError):source_match(bad,files)

    def test_empty_or_partial_runner_freeze_not_accepted(self):
        self.assertFalse(unchanged({'source_files':{}}))
        rows={f:sha(ROOT/f) for f in required_sources()}
        self.assertTrue(unchanged({'source_files':rows}))
        rows.pop('environment/package_inputs.py')
        self.assertFalse(unchanged({'source_files':rows}))

if __name__=='__main__':unittest.main()
