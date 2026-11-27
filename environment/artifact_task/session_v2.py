"""Four-action, candidate-bound session for a single engineering deliverable.

Task-specific graders are trusted callables. This adapter leaves existing RTL
policies and controllers unchanged and reuses the atomic action parser/worker.
"""
import hashlib,json,re
from pathlib import Path
VERSION='engineering-artifact-session-v2'
CATEGORIES={'test_timeout','transaction_functional_error','protocol_timing_error','pass','not_equivalent','compile_error','invalid_submission','infrastructure_error','infrastructure_timeout','proof_timeout','incomplete_comparison','transition_mismatch','insufficient_detection','legal_design_rejected','missing_activity'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,value):
    p=Path(p);tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2)+'\n');tmp.replace(p)
def prompt(filename,actions=20,tests=4):
    return ('Solve the engineering task specified by spec.md. Return exactly ONE JSON object per turn, no prose or additional actions. '+
      'Allowed actions: {"tool":"read","file":"spec.md"}, {"tool":"read","file":"'+filename+'"}, '+
      '{"tool":"edit","content":"complete file"}, {"tool":"test"}, {"tool":"submit"}. '+
      'Read both files before edit or submit. Only '+filename+' can be edited. Test runs the trusted public checker against the current file. '+
      'You have at most %d total actions and %d public tests. Rejected actions also consume an action. '%(actions,tests)+
      'Submission is allowed without passing tests and ends solving. Independent terminal and held-out results are not returned. '+
      'No shell, other files, reference, checker or private inputs are available. Do not combine actions.')
class Session:
    def __init__(self,task,work,out,grader,max_actions=20,max_tests=4):
        if type(max_actions)!=int or type(max_tests)!=int or not 1<=max_tests<max_actions<=20:raise ValueError('Invalid limits')
        self.task=task;self.filename=task['deliverable']
        if not re.fullmatch(r'[a-z][a-z0-9_]*\.(sv|json)',self.filename):raise ValueError('Invalid artifact name')
        self.work=Path(work);self.out=Path(out);self.out.mkdir(parents=True,exist_ok=False)
        self.grader=grader;self.max_actions=max_actions;self.max_tests=max_tests
        self.actions=0;self.tests=0;self.edits=0;self.read=set();self.done=False;self.submitted=False;self.trace=[]
        save(self.out/'session.json',{'version':VERSION,'task_id':task['task_id'],'deliverable':self.filename,'max_actions':max_actions,'max_tests':max_tests,'initial_sha256':sha(self.work/self.filename)})
    def handle(self,a):
        if self.done:return {'status':'REJECTED','reason':'episode_closed'}
        self.actions+=1;executed=False;obs={'status':'REJECTED','reason':'invalid_action_format'}
        schemas={'read':{'tool','file'},'edit':{'tool','content'},'test':{'tool'},'submit':{'tool'}}
        if not isinstance(a,dict):a={}
        tool=a.get('tool');path=self.work/self.filename
        if tool in schemas and set(a)==schemas[tool]:
            if tool=='read':
                if a['file'] in ('spec.md',self.filename):
                    self.read.add(a['file']);executed=True;obs={'file':a['file'],'content':(self.work/a['file']).read_text()}
                else:obs={'status':'REJECTED','reason':'file_not_allowed'}
            elif tool in ('edit','submit') and self.read!={'spec.md',self.filename}:obs={'status':'REJECTED','reason':'read_both_first'}
            elif tool=='edit':
                content=a['content']
                if isinstance(content,str) and 0<len(content.encode())<=24000:
                    path.write_text(content);self.edits+=1;executed=True
                    (self.out/('candidate-%02d'%self.actions+path.suffix)).write_bytes(path.read_bytes())
                    obs={'status':'EDITED','source_sha256':sha(path)}
                else:obs={'status':'REJECTED','reason':'invalid_content'}
            elif tool=='test':
                if self.tests>=self.max_tests:obs={'status':'REJECTED','reason':'test_budget_exhausted'}
                else:
                    self.tests+=1;executed=True;h=sha(path)
                    try:r=self.grader(path,self.out/('public-%02d'%self.actions),'public')
                    except Exception as e:
                        save(self.out/('internal-error-%02d.json'%self.actions),{'exception_type':type(e).__name__})
                        r={'reward':None,'category':'infrastructure_error','source_sha256':h}
                    if r.get('source_sha256')!=h or sha(path)!=h:raise RuntimeError('Candidate/result mismatch')
                    category=r.get('category');category=category if category in CATEGORIES else 'infrastructure_error'
                    status='PASS' if r.get('reward')==1 else 'FAIL' if r.get('reward')==0 else 'INVALID' if category=='invalid_submission' else 'ENV_ERROR'
                    obs={'status':status,'category':category,'source_sha256':h,'remaining_test_calls':self.max_tests-self.tests}
            elif tool=='submit':
                dest=self.out/'submission';dest.mkdir();f=dest/self.filename;f.write_bytes(path.read_bytes());f.chmod(0o444)
                self.submitted=True;self.done=True;executed=True;obs={'status':'SUBMITTED','source_sha256':sha(f)}
        if obs.get('reason')=='invalid_action_format':
            obs['instruction']='No action from this reply was executed. Return exactly one JSON object without prose, fences or another action. Wait for its result before choosing the next action.'
        self.trace.append({'action_index':self.actions,'action':a,'executed':executed,'observation':obs,'observation_delivered':False})
        save(self.out/'trace.json',self.trace)
        if self.actions>=self.max_actions:self.done=True
        return obs
    def finalize(self,solver_stopped):
        if solver_stopped is not True:raise ValueError('Solver must stop before grading')
        if not self.submitted:return {'reward':None,'category':'agent_incomplete'}
        p=self.out/'submission'/self.filename;h=sha(p)
        r=self.grader(p,self.out/'terminal','terminal')
        if r.get('source_sha256')!=h or sha(p)!=h:raise RuntimeError('Submission changed')
        return r
