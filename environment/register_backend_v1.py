"""Source-bound SSH adapter for locally generated finite APB register materials.

Only a fixed trusted runner and one candidate are deployed. No solver command,
checker path or control-bank variant enters this interface. Each grade gets a
fresh build; reconnecting collects the same job, never silently regrades it.
"""
import hashlib
import io
import json
import shlex
import subprocess
import tarfile
import time
import uuid
from pathlib import Path
from environment.register_instance_controls import inputs as verify_materials
from environment.register_inputs_v1 import derive
from task_families.apb_register_v1.campaign import source_policy
from task_families.apb_register_v1.results import simulation_result
from task_families.apb_register_v1.verification import config_sv, anchors_sv
from task_families.router_v3.toolchain import observed, check as check_toolchain

ROOT = Path(__file__).resolve().parents[1]
EXECUTION_FILES = ['environment/'+n for n in (
    'durable_job.py', 'register_remote_v1.py', 'register_inputs_v1.py')]
EXECUTION_FILES += [
    'task_families/apb_register_v1/'+n for n in (
        '__init__.py', 'contract.py', 'generate.py', 'verification.py',
        'campaign.py', 'results.py', 'tb.sv.in')]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read(p):
    return json.loads(Path(p).read_text())


def save(p, value):
    Path(p).write_text(json.dumps(value, indent=2)+'\n')


class Backend:
    def __init__(self, package, manifest_sha256, config, inputs, seeds):
        self.package = Path(package).resolve()
        self.manifest_sha256 = manifest_sha256
        self.config = Path(config).resolve()
        self.config_sha256 = sha(self.config)
        self.cfg = read(self.config)
        self.seeds = seeds.copy()
        if set(inputs) != {'public', 'terminal', 'heldout'}:
            raise ValueError('Three separate input roles required')
        self.inputs = {k: Path(v).resolve() for k, v in inputs.items()}
        if len(set(self.inputs.values())) != 3:
            raise ValueError('Separate role input files required')
        self.input_sha256 = {k: sha(v) for k, v in self.inputs.items()}
        self.sources = {n: sha(ROOT/n) for n in EXECUTION_FILES}
        self.contract, meta = verify_materials(self.package)
        self.task = dict(meta, deliverable='bridge.sv')
        self.taskdir = self.package
        self.check()

    def check(self):
        if sha(self.package/'manifest.json') != self.manifest_sha256:
            raise ValueError('Material identity changed')
        contract, _ = verify_materials(self.package)
        if sha(self.config) != self.config_sha256:
            raise ValueError('Configuration changed')
        for name in ('host', 'ssh_config', 'remote_root', 'eda_env_script', 'apb_vip_root'):
            value = self.cfg.get(name)
            if not isinstance(value, str) or not value or any(c in value for c in '\x00\r\n'):
                raise ValueError('Missing or invalid deployment configuration')
        if not self.cfg['remote_root'].startswith('/'):
            raise ValueError('Absolute execution root required')
        expected_env = self.cfg.get('environment_entry_sha256')
        if not isinstance(expected_env, str) or len(expected_env) != 64 or any(c not in '0123456789abcdef' for c in expected_env):
            raise ValueError('Frozen environment entry digest required')
        if 'variant' in self.cfg or self.cfg.get('compile_cache'):
            raise ValueError('No control-bank variants or external caches')
        expected = derive(contract, self.seeds)
        if any(sha(p) != self.input_sha256[k] or read(p) != expected[k]
               for k, p in self.inputs.items()):
            raise ValueError('Complete frozen input differs')
        if any(sha(ROOT/n) != h for n, h in self.sources.items()):
            raise ValueError('Execution source changed')

    def remote(self, command, data=None, timeout=40):
        p = subprocess.run(['ssh', '-F', self.cfg['ssh_config'], self.cfg['host'],
                            'bash -lc '+shlex.quote(command)], input=data,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        if p.returncode:
            raise RuntimeError('Remote operation failed, exit '+str(p.returncode))
        return p.stdout

    def grade(self, source, out, phase):
        self.check()
        if phase not in self.inputs:
            raise ValueError('Unknown evaluation role')
        source = Path(source).resolve()
        out = Path(out).resolve()
        out.mkdir(parents=True, exist_ok=False)
        h = sha(source)
        (out/'candidate.sv').write_bytes(source.read_bytes())
        if sha(out/'candidate.sv') != h:
            raise ValueError('Candidate changed during freezing')
        bad = source_policy((out/'candidate.sv').read_text())
        if bad:
            r = dict(reward=None, category='invalid_submission', reason=bad,
                     verification_complete=False, source_sha256=h, evaluation_role=phase)
            save(out/'result.json', r)
            return r
        release = self.cfg['remote_root']+'/register-grade-'+uuid.uuid4().hex
        local_config = {k: self.cfg[k] for k in ('eda_env_script', 'apb_vip_root')}
        files = {n: (ROOT/n).read_bytes() for n in EXECUTION_FILES}
        files.update({'candidate.sv': (out/'candidate.sv').read_bytes(),
                      'contract.json': (self.package/'contract.json').read_bytes(),
                      'input.json': self.inputs[phase].read_bytes(),
                      'config.json': (json.dumps(local_config, indent=2)+'\n').encode()})
        request = dict(role=phase, seeds=self.seeds, files={
            n: hashlib.sha256(raw).hexdigest() for n, raw in files.items()})
        files['request.json'] = (json.dumps(request, indent=2)+'\n').encode()
        # This record precedes all remote mutations. On interruption use collect;
        # never start a second job under the original result directory.
        save(out/'deployment.json', dict(schema='register-deployment-v1', release=release,
             role=phase, source_sha256=h, package_manifest_sha256=self.manifest_sha256,
             config_sha256=self.config_sha256, input_sha256=self.input_sha256[phase],
             sources=self.sources, request=request))
        probe = "import shutil;from pathlib import Path;busy=[]\nfor p in Path('/proc').glob('[0-9]*/comm'):\n try:\n  if p.read_text().strip() in ('simv','vcs','vcs1','dc_shell','fm_shell'):busy.append(p.parent.name)\n except FileNotFoundError:pass\nassert not busy;assert shutil.disk_usage("+repr(self.cfg['remote_root'])+").free>=4*1024**3"
        self.remote('python3 -c '+shlex.quote(probe))
        data = io.BytesIO()
        with tarfile.open(fileobj=data, mode='w:gz') as tar:
            for name, raw in files.items():
                info = tarfile.TarInfo(name)
                info.size = len(raw)
                tar.addfile(info, io.BytesIO(raw))
        self.remote('umask 077; mkdir '+shlex.quote(release)+' && tar -xzf - -C '+shlex.quote(release), data.getvalue(), 90)
        self.remote('cd '+shlex.quote(release)+' && python3 -m environment.durable_job',
                    json.dumps(dict(name='grade', module='environment.register_remote_v1', args=[])).encode())
        result = self.collect(out)
        if sha(source) != h:
            raise ValueError('Source changed during grading')
        return result

    def collect(self, out):
        """Recover only the recorded remote job; no compile/simulation is started."""
        self.check()
        out = Path(out).resolve()
        d = read(out/'deployment.json')
        phase = d['role']
        if (d['config_sha256'] != self.config_sha256 or d['sources'] != self.sources
                or d['package_manifest_sha256'] != self.manifest_sha256
                or d['input_sha256'] != self.input_sha256[phase]):
            raise ValueError('Recovery dependency differs')
        release = d['release']
        if not release.startswith(self.cfg['remote_root']+'/register-grade-'):
            raise ValueError('Unexpected recovery location')
        start = time.monotonic()
        while True:
            state = json.loads(self.remote('cat '+shlex.quote(release+'/.jobs/grade/state.json')))
            if state['status'] == 'finished':
                break
            if time.monotonic()-start > 850:
                raise TimeoutError('Collection bound; preserve job for explicit recovery')
            print(json.dumps(dict(status='register_grade_running', role=phase)), flush=True)
            time.sleep(15)
        save(out/'job.json', state)
        # Archive only frozen inputs and grading records; derived binaries and
        # commercial library links never leave the licensed machine.
        collect = "import os,subprocess;from pathlib import Path\nif not Path('result.tgz').exists():\n subprocess.run(['tar','--exclude=build','--exclude=__pycache__','-czf','result.part','grade','resource.json','request.json','config.json','input.json','contract.json','candidate.sv'],check=True)\n os.replace('result.part','result.tgz')"
        digest = self.remote('cd '+shlex.quote(release)+' && python3 -c '+shlex.quote(collect)+' && sha256sum result.tgz', timeout=90).decode().split()[0]
        raw = self.remote('cat '+shlex.quote(release+'/result.tgz'), timeout=90)
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError('Evidence transfer differs')
        archive = out/'evidence.tgz'
        if archive.exists():
            if sha(archive) != digest:
                raise ValueError('Recovery would overwrite different evidence')
        else:
            archive.write_bytes(raw)
        evidence = out/'evidence'
        if not evidence.exists():
            evidence.mkdir()
            with tarfile.open(fileobj=io.BytesIO(raw)) as tar:
                for m in tar.getmembers():
                    if (not (m.isfile() or m.isdir()) or Path(m.name).is_absolute()
                            or '..' in Path(m.name).parts):
                        raise ValueError('Unsafe evidence archive member')
                tar.extractall(str(evidence))
        self.check()
        if read(evidence/'request.json') != d['request']:
            raise ValueError('Executed request differs')
        for name in ('candidate.sv', 'contract.json', 'input.json', 'config.json'):
            if sha(evidence/name) != d['request']['files'][name]:
                raise ValueError('Executed input changed')
        grade = evidence/'grade'
        result = read(grade/'result.json')
        resource = read(evidence/'resource.json')
        if result['source_sha256'] != d['source_sha256'] or result['grader_sha256'] != self.sources['task_families/apb_register_v1/campaign.py']:
            raise ValueError('Graded source differs')
        if state.get('exit_code') or resource['exit_code'] or resource['stopped_reason']:
            result = dict(result, reward=None, category='infrastructure_error', verification_complete=False)
        if (grade/'vectors.txt').exists():
            rows = read(self.inputs[phase])['vectors']
            expected = ''.join('%d %08x %08x %x\n'%tuple(x) for x in rows)
            if (grade/'vectors.txt').read_text() != expected or sha(grade/'candidate.sv') != d['source_sha256']:
                raise ValueError('Actual candidate or vectors differ')
            if (sha(grade/'tb.sv') != self.sources['task_families/apb_register_v1/tb.sv.in']
                    or (grade/'register_config.svh').read_text() != config_sv(self.contract)
                    or (grade/'oracle_anchors.svh').read_text() != anchors_sv(self.contract)):
                raise ValueError('Actual checker differs from contract')
        if (grade/'backend.json').exists():
            backend = read(grade/'backend.json')
            if (backend.get('compiled') is not True
                    or backend['inputs']['environment_entry'] != self.cfg['environment_entry_sha256']
                    or backend['inputs']['configuration'] != sha(evidence/'config.json')
                    or backend['inputs']['grader'] != result['grader_sha256']
                    or any(backend['inputs'][n] != sha(grade/n) for n in
                           ('candidate.sv', 'tb.sv', 'register_config.svh', 'oracle_anchors.svh'))):
                raise ValueError('Compiled dependency binding differs')
        if (grade/'simulation.log').exists():
            log = (grade/'simulation.log').read_text()
            check_toolchain(observed(log), self.cfg['toolchain'])
            rows = read(self.inputs[phase])['vectors']
            transfers = sum(x[0] != 2 for x in rows)
            projected = simulation_result(log, result['simulation_exit'], transfers,
                1+sum(x[0] == 2 for x in rows), transfers*self.contract['wait_cycles'], len(self.contract['registers']))
            if any(result[k] != projected[k] for k in ('reward', 'category', 'verification_complete')):
                raise ValueError('Result differs from actual simulation')
        if result['reward'] == 1 and not result['verification_complete']:
            raise ValueError('Incomplete successful grade')
        result = dict(result, evaluation_role=phase, input_seed=self.seeds[phase],
                      frozen_input_sha256=self.input_sha256[phase], package_manifest_sha256=self.manifest_sha256,
                      evidence_sha256=digest)
        if (out/'result.json').exists() and read(out/'result.json') != result:
            raise ValueError('Recovery would overwrite a different result')
        save(out/'result.json', result)
        return result
