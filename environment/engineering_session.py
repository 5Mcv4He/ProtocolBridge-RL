"""Opt-in Task003 engineering capability profile, separate from Policy v1."""
import json
from pathlib import Path
from environment.task003 import Session as BaseSession
from environment.engineering_tools import compile_rtl,inspect_public,VERSION

PROFILE={'id':VERSION,'task_id':'axil_to_apb4_queue_003','max_compile_calls':2,
         'max_inspect_calls':2,'max_observation_chars':1200,'max_agent_actions':20,
         'tools':['compile','inspect'],'inspect_scope':'most recent actual public test only'}

def extend_prompt(prompt):
    return prompt+' Additional engineering-tools-v1 actions: {"tool":"compile"} compiles your current RTL with VCS without running functional tests (at most 2 calls). {"tool":"inspect"} queries the first failed checker of your most recent public test using a fixed requirement-level message (at most 2 calls); it does not run simulation. Read both files first. These actions share the same 20-action episode budget. Compiler PASS is not proof of functional correctness. No full logs, private results, arbitrary commands or files are accessible.'

class Session(BaseSession):
    def __init__(self,*a,**kw):
        self.compiler=kw.pop('compiler',compile_rtl)
        super().__init__(*a,**kw)
        if self.policy['policy_id']!='test_diagnostic':raise ValueError('Engineering profile requires diagnostic policy')
        self.compiles=0;self.inspects=0
        (self.out/'capabilities.json').write_text(json.dumps(PROFILE,indent=2))
    def handle(self,action):
        tool=action.get('tool') if isinstance(action,dict) else None
        if tool not in PROFILE['tools']:return super().handle(action)
        if self.done or self.actions>=20:return {'status':'REJECTED','reason':'episode_closed'}
        self.actions+=1;executed=False;obs={'status':'REJECTED','reason':'invalid_action'}
        if set(action)!={'tool'}:pass
        elif self.read!=set(self.policy['readable_files']):obs['reason']='read_spec_and_rtl_first'
        elif tool=='compile':
            if self.compiles>=2:obs['reason']='compile_budget_exhausted'
            else:
                self.compiles+=1;executed=True
                try:obs=self.compiler(self.work/'bridge.sv',self.out/('compile-%02d'%self.actions))
                except Exception:obs={'status':'ENV_ERROR','diagnostics':[],'functional_correctness_checked':False}
                obs=dict(obs,remaining_compile_calls=2-self.compiles)
        elif not self.public:obs['reason']='no_public_result'
        elif self.inspects>=2:obs['reason']='inspect_budget_exhausted'
        else:
            self.inspects+=1;executed=True;last=self.public[-1]
            obs=dict(inspect_public(last['result']),public_action=last['action'],
                     source_sha256=last['source_sha256'],remaining_inspect_calls=2-self.inspects)
        if len(json.dumps(obs))>1200:raise RuntimeError('Engineering observation exceeded bound')
        self.trace.append({'action_index':self.actions,'action':action,'executed':executed,'observation':obs})
        (self.out/'trace.json').write_text(json.dumps(self.trace,indent=2))
        if self.actions>=20:self.done=True
        return obs
