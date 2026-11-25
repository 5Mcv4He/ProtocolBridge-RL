import shlex, unittest
from environment.remote_backend import remote_command, toolchain_metadata

class BackendOptions(unittest.TestCase):
    def test_default_unchanged(self):
        self.assertEqual(remote_command({}, 'echo ok'), 'echo ok')

    def test_shell_keeps_program_one_argument(self):
        command = "cd '/path with spaces' && python3 -c 'print(1)'"
        self.assertEqual(shlex.split(remote_command({'remote_shell':'bash'}, command)), ['bash','-lc',command])

    def test_reject_unknown_shell(self):
        with self.assertRaises(ValueError): remote_command({'remote_shell':'bash; false'}, 'true')

    def test_no_deployment_paths_in_metadata(self):
        with self.assertRaises(ValueError): toolchain_metadata({'toolchain':{'license_path':'private'}})
        self.assertEqual(toolchain_metadata({'toolchain':{'uvm':'1.2'}}), {'uvm':'1.2'})

    def test_environment_entry_is_quoted_and_fail_closed(self):
        import subprocess
        cfg={'eda_env_script':'/missing path/env.sh'}
        args=shlex.split(remote_command(cfg,'printf SHOULD_NOT_RUN'))
        self.assertEqual(args[:2],['bash','-lc'])
        p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        self.assertEqual(p.returncode,125);self.assertNotIn(b'SHOULD_NOT_RUN',p.stdout)
        for value in ('relative/path','/bad\npath',False):
            with self.assertRaises(ValueError):remote_command({'eda_env_script':value},'true')
