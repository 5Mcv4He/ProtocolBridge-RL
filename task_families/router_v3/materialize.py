"""Versioned deployment adaptation of a frozen router-v2 candidate.

No protocol, scoreboard, stimulus or reward changes. Runtime artifacts may be
linked within one strictly bound control build; simulation is always executed.
"""
import argparse, hashlib, json, shutil, subprocess
from pathlib import Path
from task_families.router_v2.generate import verify, sha
ROOT = Path(__file__).resolve().parents[2]
DIRS = ('environment', 'verifier', 'fixtures', 'tasks', 'tests', 'scripts')


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Inherited deployment source does not match adapter')
    return text.replace(old, new, 1)


def adapt(text):
    # The command wrapper sources the configured environment in every fresh
    # shell, including local execution whose child environment is filtered.
    text = replace_once(text,
        "        def shell(command,timeout):return run((['/bin/bash','-lc',command] if local else ssh+[command]),timeout)",
        """        def shell(command,timeout):
            entry=cfg.get('eda_env_script')
            if not isinstance(entry,str) or not entry.startswith('/') or any(x in entry for x in '\\x00\\n\\r'):
                raise ValueError('An explicit absolute EDA environment entry is required')
            command='source '+shlex.quote(entry)+' || exit 125; '+command
            return run((['/bin/bash','-lc',command] if local else ssh+['bash -lc '+shlex.quote(command)]),timeout)
        rc,environment_identity=shell('sha256sum '+shlex.quote(cfg['eda_env_script']),30)
        if rc:raise RuntimeError('Cannot identify execution environment')
        inputs['build_configuration']=hashlib.sha256(json.dumps({k:v for k,v in cfg.items() if k not in ('variant','remote_root')},sort_keys=True).encode()).hexdigest()
        inputs['environment_entry']=hashlib.sha256(environment_identity.encode()).hexdigest()
        inputs['campaign']=sha(Path(__file__))
""")
    text = text.replace("cmd='source ~/.bashrc; cd '", "cmd='cd '")
    text = text.replace("cmd='source ~/.bashrc; export DESIGNWARE_HOME='", "cmd='export DESIGNWARE_HOME='")
    text = replace_once(text,
        "            rc,log=shell('cp -a '+assets+' '+shlex.quote(remote+'/'),120)",
        """            # Each run has private vectors/logs. Links point only to a bound,
            # completed build, never to another candidate's evaluated result.
            rc,log=shell('cp -as '+assets+' '+shlex.quote(remote+'/'),120)""")
    text = replace_once(text,
        "        (out/'backend.json').write_text(json.dumps({'remote':remote,'inputs':inputs},indent=2))",
        "        (out/'backend.json').write_text(json.dumps({'remote':remote,'inputs':inputs,'execution_adapter':'router-deployment-v1'},indent=2))")
    return text


def materialize(parent, out):
    parent, out = Path(parent).resolve(), Path(out).resolve()
    m = verify(parent)
    if m.get('family') != 'x2p_three_target_router_v2':
        raise ValueError('Expected a frozen router-v2 candidate')
    if out.exists():
        raise ValueError('Never overwrite a package')
    out.mkdir(parents=True)
    for name in m['files']:
        p = Path(name)
        if True:  # Preserve inherited test dependencies, including frozen baseline evidence.

            dest = out / p
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(str(parent / p), str(dest))
    campaign = out / 'verifier/task002/campaign.py'
    campaign.write_text(adapt(campaign.read_text()))
    driver = out/'task_families/router_v3/qualification.py'
    driver.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(str(Path(__file__).with_name('qualification.py')), str(driver))
    (out/'.local').mkdir()
    import sys
    test = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-q'], cwd=str(out), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (out/'.local/adapter-tests.log').write_bytes(test.stdout)
    if test.returncode:
        raise RuntimeError('Adapted package tests failed; preserved for diagnosis')
    files = {str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file() and not set(p.relative_to(out).parts)&{'.local','__pycache__'}}
    manifest = dict(m, files=files, family='x2p_three_target_router_v3',
                    execution_adapter='router-deployment-v1',
                    parent_manifest_sha256=sha(parent/'family-manifest.json'),
                    adapter_sha256=sha(Path(__file__)), status='candidate_not_admitted')
    (out/'family-manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True)+'\n')
    verify(out)
    return manifest

if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('parent');p.add_argument('out');a=p.parse_args()
    m=materialize(a.parent,a.out);print(json.dumps({'task_id':m['task_id'],'status':m['status']}))
