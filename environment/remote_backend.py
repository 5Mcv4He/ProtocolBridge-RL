"""Deployment options only; no task or verification semantics."""
import shlex

def remote_command(config, command):
    entry=config.get('eda_env_script')
    if entry is not None:
        if not isinstance(entry,str) or not entry.startswith('/') or any(x in entry for x in '\x00\n\r'):raise ValueError('Invalid EDA environment entry')
        command='source '+shlex.quote(entry)+' || exit 125; '+command
    shell = config.get('remote_shell')
    if shell is None:
        return 'bash -lc '+shlex.quote(command) if entry is not None else command
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
