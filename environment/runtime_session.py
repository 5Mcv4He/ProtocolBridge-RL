"""Matched laboratory permissions; two profiles differ only in feedback projection."""
import json
from environment.task003 import Session as Base
from environment.runtime_tools import run,observation,cases,sha,PUBLIC
PROFILES=('runtime-verdict-v1','runtime-observe-v1')
def profile(name):
    if name not in PROFILES:raise ValueError('Unknown runtime profile')
    return {'id':name,'task_id':'axil_to_apb4_queue_003','tools':['experiment','observe'],
            'max_experiment_calls':3,'max_observe_calls':4,'max_agent_actions':20,
            'max_observation_chars':16000,'feedback':'timeline' if name==PROFILES[1] else 'verdict'}
def extend_prompt(prompt,capability):
    p=profile(capability)
    return prompt+' Runtime laboratory actions: {"tool":"experiment","scenario":"write_fifo"} selects one public scenario ('+', '.join(PUBLIC)+'). Alternatively {"tool":"experiment","transactions":[[1,256,123,15,0,0,4,16,0,0]]} supplies 1..16 rows [write,address,data,strobe,address_delay,data_delay,APB_wait,response_stall,error,start_delay]; write/error 0..1, aligned 32-bit address, 32-bit data, strobe 0..15, delays/waits/stalls 0..64. Named reset scenarios are supported; custom reset is not. At most 3 experiment invocations. {"tool":"observe","start":0,"count":8} queries the most recent laboratory run (start 0..4095, count 1..12 cycles, at most 4 queries). Lab results apply to the recorded candidate, not later edits. Read both files first. These actions share 20 total actions; 2 full public tests remain unchanged. Laboratory PASS is not terminal reward. No shell, arbitrary signals, files, SystemVerilog testbench or private cases. Laboratory feedback mode: '+p['feedback']+'. Timeline mode returns sampled interface pins, handshakes and externally counted unretired AW/W/AR credits. Pre samples precede the rising-edge checker; post samples are one simulation time unit after the edge; post is not another handshake. The first-error window may end immediately at the failing edge. Internal arbitration is not observed: APB setup identifies the selected direction. X/Z are null. Verdict mode returns only status. First read the files and test the starting candidate before repairing it.'
class Session(Base):
    def __init__(self,*args,**kwargs):
        self.capability=kwargs.pop('capability');self.profile=profile(self.capability)
        self.experimenter=kwargs.pop('experimenter',run)
        super().__init__(*args,**kwargs)
        if self.policy['policy_id']!='test_diagnostic':raise ValueError('Runtime requires E policy')
        self.experiments=0;self.observes=0;self.lab=[];self.lab_builds={}
        (self.out/'capabilities.json').write_text(json.dumps(self.profile,indent=2))
    def handle(self,action):
        tool=action.get('tool') if isinstance(action,dict) else None
        if tool not in self.profile['tools']:
            obs=super().handle(action)
            if obs.get('reason') in ('invalid_action','invalid_action_format') and 'action_fields' in obs:
                obs['action_fields'].update(experiment=['tool','scenario OR transactions'],observe=['tool','start','count'])
                (self.out/'trace.json').write_text(json.dumps(self.trace,indent=2))
            return obs
        if self.done or self.actions>=20:return {'status':'REJECTED','reason':'episode_closed'}
        self.actions+=1;executed=False;obs={'status':'REJECTED','reason':'invalid_action'}
        if self.read!=set(self.policy['readable_files']):obs['reason']='read_spec_and_rtl_first'
        elif tool=='experiment':
            request={k:v for k,v in action.items() if k!='tool'}
            try:cases(request);valid=True
            except (ValueError,TypeError):valid=False
            if not valid:pass
            elif self.experiments>=3:obs['reason']='experiment_budget_exhausted'
            else:
                self.experiments+=1;executed=True;dest=self.out/('experiment-%02d'%self.actions);source=self.work/'bridge.sv';key=sha(source)
                try:r=self.experimenter(source,dest,request,self.lab_builds.get(key))
                except Exception:r={'status':'ENV_ERROR','source_sha256':key,'reward':None}
                if (dest/'grade/backend.json').exists():self.lab_builds[key]=str(dest/'grade')
                self.lab.append({'action':self.actions,'result':r})
                obs=observation(r,self.capability==PROFILES[1])
                obs['remaining_experiment_calls']=3-self.experiments
        elif set(action)!={'tool','start','count'} or type(action['start'])!=int or type(action['count'])!=int or not 0<=action['start']<4096 or not 1<=action['count']<=12:pass
        elif not self.lab:obs['reason']='no_experiment_result'
        elif self.observes>=4:obs['reason']='observe_budget_exhausted'
        else:
            self.observes+=1;executed=True
            obs=observation(self.lab[-1]['result'],self.capability==PROFILES[1],action['start'],action['count'])
            obs.update(experiment_action=self.lab[-1]['action'],remaining_observe_calls=4-self.observes)
        if len(json.dumps(obs))>16000:raise RuntimeError('Runtime observation bound')
        self.trace.append({'action_index':self.actions,'action':action,'executed':executed,'observation':obs})
        (self.out/'trace.json').write_text(json.dumps(self.trace,indent=2))
        if self.actions>=20:self.done=True
        return obs
