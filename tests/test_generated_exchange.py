import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts.generated_exchange import export


class GeneratedExchange(unittest.TestCase):
    def test_unknown_profile_cannot_import_or_create_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'plan.json';p.write_text(json.dumps({'schema':'arbitrary.module'}))
            with self.assertRaises(ValueError):export(p,Path(tmp)/'runs',Path(tmp)/'out')
            self.assertFalse((Path(tmp)/'out').exists())

    def test_explicit_profiles_keep_own_auditor(self):
        profiles={'native-router-package-study-v2':'package_exchange',
                  'native-register-material-study-v1':'register_exchange',
                  'native-composed-package-study-v1':'composed_exchange'}
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'plan.json'
            for schema,module in profiles.items():
                p.write_text(json.dumps({'schema':schema}))
                with patch('scripts.'+module+'.export',return_value={'records':1}) as impl:
                    self.assertEqual(export(p,'runs','out'),{'records':1})
                    impl.assert_called_once_with(p,'runs','out')


if __name__=='__main__':unittest.main()
