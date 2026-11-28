"""Qualified router capsule adapter; no task-ID-specific grader dispatch.

Only trusted, locally produced packages are supported. A source manifest checks
integrity, not the safety of executing arbitrary third-party Python code.
Public, terminal and held-out inputs are frozen separately by the caller.
"""
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
from task_families.router_v2.generate import verify
from environment.package_inputs import seeds_checked
from task_families.router_v3.toolchain import observed,check as check_toolchain

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

class Backend:
    def __init__(self,package,manifest_sha256,config,inputs,seeds):
        self.package=Path(package).resolve();self.manifest_sha256=manifest_sha256
        self.config=Path(config).resolve();self.config_sha256=sha(self.config)
        if set(inputs)!= {'public','terminal','heldout'}:raise ValueError('Three separate input roles required')
        self.seeds=seeds_checked(seeds)
        self.inputs={k:Path(v).resolve() for k,v in inputs.items()}
        if len(set(self.inputs.values()))!=3:raise ValueError('Separate role input files required')
        self.input_sha256={k:sha(v) for k,v in self.inputs.items()}
        self.check()
        m=json.loads((self.package/'family-manifest.json').read_text())
        self.taskdir=self.package/'tasks'/m['task_id']
        meta=json.loads((self.taskdir/'task.json').read_text())
        if meta['verifier']!='verifier.task002.campaign':raise ValueError('Unsupported qualified backend')
        self.task=dict(meta,deliverable='bridge.sv')
        self.validate_complete_inputs()

    def check(self):
        if sha(self.package/'family-manifest.json')!=self.manifest_sha256:raise ValueError('Package identity changed')
        m=verify(self.package)
        if m.get('family')!='x2p_three_target_router_v3' or m.get('execution_adapter')!='router-deployment-v1':raise ValueError('Unsupported execution package')
        if sha(self.config)!=self.config_sha256:raise ValueError('Execution configuration changed')
        cfg=json.loads(self.config.read_text())
        if 'variant' in cfg or cfg.get('compile_cache'):raise ValueError('Standalone grading cannot select a control-bank variant or external cache')
        if any(sha(p)!=self.input_sha256[k] for k,p in self.inputs.items()):raise ValueError('Frozen inputs changed')

    def validate_complete_inputs(self):
        self.check()
        env={k:os.environ[k] for k in ('PATH','HOME','LANG') if k in os.environ}
        cmd=[sys.executable,str(Path(__file__).with_name('package_inputs.py')),json.dumps(self.seeds)]
        p=subprocess.run(cmd,cwd=str(self.package),env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=60)
        if p.returncode:raise ValueError('Cannot derive complete input roles')
        expected=json.loads(p.stdout)
        for role,path in self.inputs.items():
            if json.loads(path.read_text())!=expected[role]:
                raise ValueError('Input is not the complete frozen '+role+' suite')
        self.check()

    def grade(self,source,out,phase):
        if phase not in self.inputs:raise ValueError('Unknown evaluation role')
        self.check();source=Path(source).resolve();out=Path(out).resolve();h=sha(source)
        if out.exists():raise ValueError('Never overwrite a grading run')
        env={k:os.environ[k] for k in ('PATH','HOME','LANG','SSH_AUTH_SOCK') if k in os.environ};env['PB_CONFIG']=str(self.config);start=time.monotonic()
        # The capsule's campaign applies its own source policy before any EDA.
        # Explicit input files bind each run; no result or binary cache is passed.
        cmd=[sys.executable,str(Path(__file__).with_name('package_grade_entry.py')),str(source),str(out),str(self.inputs[phase]),phase]
        p=subprocess.run(cmd,cwd=str(self.package),env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=2400)
        if p.returncode or not (out/'result.json').is_file():
            out.mkdir(parents=True,exist_ok=True)
            (out/'adapter-process-error.json').write_text(json.dumps({'exit_code':p.returncode,'stdout':p.stdout.decode(errors='replace')[-8000:],'stderr':p.stderr.decode(errors='replace')[-8000:]},indent=2)+'\n')
            raise RuntimeError('Backend process did not produce a result')
        result=json.loads((out/'result.json').read_text())
        self.check()
        if sha(source)!=h or result.get('source_sha256')!=h:raise RuntimeError('Graded source identity differs')
        if (out/'cases.json').is_file():
            # JSON whitespace is not an input change: compare parsed structures.
            if json.loads((out/'cases.json').read_text())!=json.loads(self.inputs[phase].read_text()):raise RuntimeError('Executed input differs')
        elif result.get('reward') is not None:
            raise RuntimeError('Determinate grade without executed input record')
        for case in result.get('cases',[]):
            identity=observed((out/case['name']/'simulation.log').read_text())
            check_toolchain(identity,json.loads(self.config.read_text())['toolchain'])
        if result.get('reward')==1 and (result.get('category')!='pass' or result.get('verification_complete') is not True):
            raise RuntimeError('Incomplete successful verification')
        result['evaluation_role']=phase;result['frozen_input_sha256']=self.input_sha256[phase]
        result['input_seed']=self.seeds[phase]
        result['package_manifest_sha256']=self.manifest_sha256;result['adapter_wall_seconds']=time.monotonic()-start
        # Preserve the campaign's original result, attach provenance separately.
        (out/'adapter-provenance.json').write_text(json.dumps({k:result[k] for k in ('evaluation_role','frozen_input_sha256','input_seed','package_manifest_sha256','adapter_wall_seconds')},indent=2)+'\n')
        return result

    def heldout(self,source,out):return self.grade(source,out,'heldout')
