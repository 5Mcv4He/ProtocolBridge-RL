import subprocess,sys,tempfile,unittest
from task_families.production_lock import exclusive

class ProductionLock(unittest.TestCase):
    def test_second_process_cannot_start_until_owner_exits(self):
        code='from task_families.production_lock import exclusive; import sys\nwith exclusive(sys.argv[1]): print("ACQUIRED")'
        with tempfile.TemporaryDirectory() as directory:
            with exclusive(directory):
                denied=subprocess.run([sys.executable,'-c',code,directory],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                self.assertNotEqual(denied.returncode,0)
                self.assertNotIn(b'ACQUIRED',denied.stdout)
            accepted=subprocess.run([sys.executable,'-c',code,directory],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            self.assertEqual(accepted.returncode,0)
            self.assertIn(b'ACQUIRED',accepted.stdout)

if __name__=='__main__':unittest.main()
