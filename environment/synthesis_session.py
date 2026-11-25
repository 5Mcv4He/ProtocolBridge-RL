"""Separate capability condition: original E plus bounded DC synthesis checking."""
import json
from environment.synthesis_tools import synth_check
from environment.synthesis_projection import VERSION
PROFILE={'id':VERSION,'task_ids':['axil_to_apb4_queue_003','axil_to_apb4_decoupled_004'],
         'tools':['synth_check'],'max_synth_calls':2,'max_agent_actions':20,'max_observation_chars':1200,
         'scope':'Candidate synthesis diagnostics only; no formal, netlist, raw log or PPA observation.'}
def extend_prompt(prompt):
    return prompt+' Additional synthesis-tools-v1 action: {"tool":"synth_check"} runs bounded Design Compiler synthesis on your current RTL (at most 2 calls). Read both files first. This shares the same 20-action episode budget; the two public functional tests are unchanged. PASS means the synthesis flow completed, not that functionality is correct. Structural warnings are advisory. No shell, Tcl, library choice, netlist, private result or PPA measurement is available.'
class SynthesisMixin:
    def __init__(self,*args,**kwargs):
        self.synthesizer=kwargs.pop('synthesizer',synth_check)
        super().__init__(*args,**kwargs)
        if self.policy['policy_id']!='test_diagnostic':raise ValueError('Synthesis profile requires diagnostic policy')
        self.synth_calls=0
        (self.out/'capabilities.json').write_text(json.dumps(PROFILE,indent=2)+'\n')
    def handle(self,action):
        if not isinstance(action,dict) or action.get('tool')!='synth_check':return super().handle(action)
        if self.done or self.actions>=20:return {'status':'REJECTED','reason':'episode_closed'}
        self.actions+=1;executed=False;obs={'status':'REJECTED','reason':'invalid_action'}
        if set(action)!={'tool'}:pass
        elif self.read!=set(self.policy['readable_files']):obs['reason']='read_spec_and_rtl_first'
        elif self.synth_calls>=2:obs['reason']='synth_budget_exhausted'
        else:
            self.synth_calls+=1;executed=True
            try:obs=self.synthesizer(self.work/'bridge.sv',self.out/('synth-%02d'%self.actions))
            except Exception:obs={'status':'ENV_ERROR','diagnostics':[],'functional_correctness_checked':False}
            # Even an injected backend is not allowed to forward arbitrary fields.
            from environment.synthesis_projection import validate_observation
            obs=validate_observation(obs)
            obs['remaining_synth_calls']=2-self.synth_calls
        if len(json.dumps(obs))>1200:raise RuntimeError('Synthesis observation exceeded bound')
        self.trace.append({'action_index':self.actions,'action':action,'executed':executed,'observation':obs})
        (self.out/'trace.json').write_text(json.dumps(self.trace,indent=2)+'\n')
        if self.actions>=20:self.done=True
        return obs

def session_class(task):
    if task==PROFILE['task_ids'][0]:from environment.task003 import Session as Base
    elif task==PROFILE['task_ids'][1]:from environment.task004 import Session as Base
    else:raise ValueError('Unsupported synthesis task')
    class Session(SynthesisMixin,Base):pass
    return Session
