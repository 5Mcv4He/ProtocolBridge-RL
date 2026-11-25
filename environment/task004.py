"""Task004 candidate environment; no changes to legacy reset/test/submit defaults."""
import argparse,json,shutil
from pathlib import Path
from environment.policy_session import Session as PolicySession
from environment.feedback import project as base_project
from verifier.task004.campaign import grade,sha
from verifier.task004 import campaign
from environment.verification_timing import measured_grade
from verifier.task004.scenarios import suite
ROOT=Path(__file__).resolve().parents[1]
TASK=ROOT/'tasks/axil_to_apb4_decoupled_004'
PUBLIC_NAMES=frozenset(c['name'] for c in suite(True,17))

def project(result,policy,remaining):
    # Reuse fixed diagnostics; extend ONLY the task-owned case-name whitelist.
    out=base_project(result,policy,remaining)
    if policy['feedback_level']=='diagnostic' and out['status']=='FAIL':
        case=result.get('failed_case')
        out['first_failed_case']=case if case in PUBLIC_NAMES else None
    if len(json.dumps(out,ensure_ascii=True))>policy['max_feedback_chars']:raise ValueError('Projection exceeds budget')
    return out

class Session(PolicySession):
    def __init__(self,policy,work,out,reward_cases,grader=grade,reuse=None):
        super().__init__(policy,work,out,reward_cases,grader,reuse,projector=project)
    def verify(self,source,dest,**kwargs):
        key=sha(source)
        r=measured_grade(self.grader,source,dest,measurement_backend=campaign,reuse_build=self.builds.get(key),**kwargs)
        if (Path(dest)/'backend.json').exists():self.builds[key]=str(dest)
        return r

def reset(work):
    work=Path(work);work.mkdir(parents=True,exist_ok=False)
    for name,source in [('spec.md',TASK/'spec.md'),('bridge.sv',TASK/'workspace/bridge.sv')]:shutil.copyfile(str(source),str(work/name))
    return {'task':'axil_to_apb4_decoupled_004','workspace':str(work)}

def test(work,out):return grade(Path(work)/'bridge.sv',out,public=True)

def submit(work,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    candidate=out/'bridge.sv';shutil.copyfile(str(Path(work)/'bridge.sv'),str(candidate));candidate.chmod(0o444)
    (out/'submission.json').write_text(json.dumps({'task_id':'axil_to_apb4_decoupled_004','sha256':sha(candidate)}))
    return grade(candidate,out/'grade')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['reset','test','submit']);p.add_argument('workspace');p.add_argument('out',nargs='?');a=p.parse_args()
    if a.action!='reset' and not a.out:p.error('out required')
    print(json.dumps(reset(a.workspace) if a.action=='reset' else globals()[a.action](a.workspace,a.out),indent=2))
