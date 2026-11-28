import unittest
from task_families.router_v3.toolchain import observed,check

class RuntimeIdentity(unittest.TestCase):
    def test_actual_banner_and_mismatched_claim(self):
        log='UVM-1.1d.Synopsys\nCompiler version O-2018.09-SP2_Full64; Runtime version O-2018.09-SP2_Full64;  Today\n'
        identity=observed(log)
        self.assertTrue(check(identity,{'vcs':'O-2018.09-SP2','uvm':'1.1d.Synopsys'}))
        with self.assertRaises(ValueError):check(identity,{'vcs':'O-2018.09-SP2','uvm':'1.2'})
    def test_missing_or_ambiguous_fails_closed(self):
        for log in ('','UVM-1.2\n','UVM-1.2\nUVM-1.1d.Synopsys\nCompiler version V; Runtime version V;\n'):
            with self.assertRaises(ValueError):observed(log)

if __name__=='__main__':unittest.main()
