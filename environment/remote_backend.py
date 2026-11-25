"""Deployment options only; no task or verification semantics."""
import shlex

def remote_command(config, command):
    shell = config.get('remote_shell')
    if shell is None:
        return command
    if shell != 'bash':
        raise ValueError('Unsupported remote_shell')
    return 'bash -lc ' + shlex.quote(command)

def toolchain_metadata(config):
    value = config.get('toolchain', {})
    allowed = {'vcs', 'vip', 'uvm', 'python', 'harness', 'os'}
    if not isinstance(value, dict) or set(value) - allowed:
        raise ValueError('Invalid toolchain metadata fields')
    if any(not isinstance(v, str) or len(v) > 160 for v in value.values()):
        raise ValueError('Invalid toolchain metadata value')
    return dict(value)
