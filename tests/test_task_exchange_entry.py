import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts.export_task_rollouts import export

class ExchangeBinding(unittest.TestCase):
    def test_rejects_identity_hash_and_path_before_auditor_execution(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);package=p/'package';package.mkdir();exp=p/'exp';exp.mkdir()
            with patch('scripts.export_task_rollouts.verify',return_value={'task_id':'queue'}),patch('scripts.export_task_rollouts.subprocess.run') as launch:
                for m in [ {'task_id':'router','source_files':{}},
                           {'task_id':'queue','source_files':{}},
                           {'task_id':'queue','source_files':{'environment/../../elsewhere':'hash'}},
                           {'task_id':'queue','source_files':{'environment/missing.py':'hash'}} ]:
                    (exp/'experiment.json').write_text(json.dumps(m))
                    with self.assertRaises(ValueError):export(package,exp,p/'out')
                (package/'environment').mkdir();(package/'environment/x.py').write_text('changed')
                (exp/'experiment.json').write_text(json.dumps({'task_id':'queue','source_files':{'environment/x.py':hashlib.sha256(b'original').hexdigest()}}))
                with self.assertRaises(ValueError):export(package,exp,p/'out')
                launch.assert_not_called()

if __name__=='__main__':unittest.main()
