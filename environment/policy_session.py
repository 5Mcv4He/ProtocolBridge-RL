"""Trusted action dispatcher, shared by real UTM rollouts and mechanism tests."""
import copy,json
from pathlib import Path
from .policy import validate,policy_hash
from .feedback import project
from .verification_timing import measured_grade
from verifier.campaign import grade,sha,source_policy

class Session:
    def __init__(self,policy,work,out,reward_cases,grader=grade,reuse=None,projector=project):
        self.policy=copy.deepcopy(validate(policy));self.work=Path(work);self.out=Path(out)
        self.reward_cases=copy.deepcopy(reward_cases);self.grader=grader;self.projector=projector;self.read=set()
        self.repair=False
        self.protocol_version=1
        self.actions=0;self.tests=0;self.edits=0;self.done=False;self.submitted=False
        self.result={'reward':None,'category':'agent_incomplete'};self.trace=[];self.public=[]
        self.builds={} if reuse is None else dict(reuse);self.first_candidate=None
        self.out.mkdir(parents=True,exist_ok=False)
        (self.out/'policy.json').write_text(json.dumps(self.policy,indent=2))
        self.policy_sha=policy_hash(self.policy)
    def verify(self,source,dest,**kwargs):
        key=sha(source);reuse=self.builds.get(key)
        r=measured_grade(self.grader,source,dest,reuse_build=reuse,**kwargs)
        if (Path(dest)/'backend.json').exists():self.builds[key]=str(dest)
        return r
    def handle(self,action):
        if self.done or self.actions>=self.policy['max_agent_actions']:return {'status':'REJECTED','reason':'episode_closed'}
        self.actions+=1;executed=False;obs={'status':'REJECTED','reason':'invalid_action'}
        if not isinstance(action,dict):action={}
        tool=action.get('tool')
        schemas={'read':{'tool','file'},'edit':{'tool','content'},'test':{'tool'},'submit':{'tool'}}
        if tool is None:obs={'status':'REJECTED','reason':'invalid_action_format',
                            'instruction':'Return exactly one JSON action object, with no prose or additional actions. Wait for its result.'}
        elif tool not in self.policy['allowed_tools']:obs={'status':'REJECTED','reason':'tool_not_allowed'}
        elif set(action)!=schemas[tool]:pass
        elif tool=='read':
            if action.get('file') in self.policy['readable_files']:
                self.read.add(action['file']);obs={'file':action['file'],'content':(self.work/action['file']).read_text()};executed=True
            else:obs={'status':'REJECTED','reason':'file_not_allowed'}
        elif tool=='edit':
            if self.repair and self.tests==0:obs={'status':'REJECTED','reason':'initial_public_test_required'}
            elif self.read!=set(self.policy['readable_files']):obs={'status':'REJECTED','reason':'read_spec_and_rtl_first'}
            elif isinstance(action['content'],str) and 0<len(action['content'])<=40000:
                candidate=self.work/'bridge.sv';candidate.write_text(action['content']);self.edits+=1;executed=True
                saved=self.out/('candidate-%02d.sv'%self.actions);saved.write_bytes(candidate.read_bytes())
                if self.first_candidate is None and source_policy(candidate) is None:self.first_candidate=saved.name
                obs={'status':'EDITED'}
        elif tool=='test':
            if self.tests>=self.policy['max_public_test_calls']:obs={'status':'REJECTED','reason':'test_budget_exhausted'}
            else:
                self.tests+=1;executed=True;dest=self.out/('public-%02d'%self.actions)
                try:r=self.verify(self.work/'bridge.sv',dest,public=True)
                except Exception as e:
                    dest.mkdir(parents=True,exist_ok=True)
                    (dest/'internal-exception.json').write_text(json.dumps({'type':type(e).__name__}))
                    r={'reward':None,'category':'infrastructure_error'}
                self.public.append({'action':self.actions,'source_sha256':sha(self.work/'bridge.sv'),'result':r})
                obs=self.projector(r,self.policy,self.policy['max_public_test_calls']-self.tests)
        elif tool=='submit':
            if self.repair and self.tests==0:obs={'status':'REJECTED','reason':'initial_public_test_required'}
            elif self.read!=set(self.policy['readable_files']):obs={'status':'REJECTED','reason':'read_spec_and_rtl_first'}
            else:
                # Commit to an immutable candidate. Private verification runs only after worker stop.
                dest=self.out/'submission';dest.mkdir();candidate=dest/'bridge.sv'
                candidate.write_bytes((self.work/'bridge.sv').read_bytes());candidate.chmod(0o444)
                self.done=True;self.submitted=True;executed=True;obs={'status':'SUBMITTED'}
        if self.protocol_version==2 and obs.get('reason') in ('invalid_action','invalid_action_format'):
            obs['instruction']='Resend ONE action object with exactly the listed fields. Do not append another action. The rejected reply executed nothing.'
            obs['action_fields']={name:sorted(schemas[name]) for name in self.policy['allowed_tools']}
        event={'action_index':self.actions,'action':action,'executed':executed,'observation':obs}
        self.trace.append(event);(self.out/'trace.json').write_text(json.dumps(self.trace,indent=2))
        if self.actions>=self.policy['max_agent_actions']:self.done=True
        return obs
    def finalize(self):
        if self.submitted:
            candidate=self.out/'submission/bridge.sv'
            self.result=self.verify(candidate,self.out/'submission/grade',cases=self.reward_cases)
        return self.result
