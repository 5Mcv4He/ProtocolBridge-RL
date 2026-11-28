import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from environment.package_inputs import seeds_checked
from environment.package_backend import Backend

class InputRoles(unittest.TestCase):
    def test_seeds_require_exact_roles_and_integers(self):
        good={'public':17,'terminal':23,'heldout':31}
        self.assertEqual(seeds_checked(good),good)
        for bad in ({},dict(good,private=1),dict(good,terminal=True),dict(good,heldout=-1)):
            with self.assertRaises(ValueError):seeds_checked(bad)

    def test_reduced_or_wrong_role_inputs_rejected_before_grading(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);expected={r:[{'role':r,'n':n} for n in range(2)] for r in ('public','terminal','heldout')}
            b=Backend.__new__(Backend);b.package=root;b.seeds={'public':17,'terminal':23,'heldout':31};b.check=lambda:None
            b.inputs={r:root/(r+'.json') for r in expected}
            for r,p in b.inputs.items():p.write_text(json.dumps(expected[r]))
            with patch('environment.package_backend.subprocess.run',return_value=SimpleNamespace(returncode=0,stdout=json.dumps(expected).encode())):
                b.validate_complete_inputs()
                b.inputs['terminal'].write_text(json.dumps(expected['terminal'][:1]))
                with self.assertRaises(ValueError):b.validate_complete_inputs()
                b.inputs['terminal'].write_text(json.dumps(expected['public']))
                with self.assertRaises(ValueError):b.validate_complete_inputs()

if __name__=='__main__':unittest.main()
