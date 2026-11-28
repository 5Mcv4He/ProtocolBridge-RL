"""Real grader/Session acceptance. No model inference; references remain trusted."""
import argparse,json,shutil
from pathlib import Path
from environment.artifact_task.session_v4 import Session,sha,save
from environment.artifact_task.dispatch_v10 import graders,ROOT
from environment.native_tools.controller_v3 import Controller

def run(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False);rows=[]
    for mode in ('rw','w1c'):
        task='register_checker_'+mode+'_v1';td=ROOT/'tasks'/task;work=out/mode;work.mkdir()
        for n,s in [('spec.md',td/'spec.md'),('checker.sv',td/'workspace/checker.sv')]:shutil.copyfile(s,work/n)
        grade,evaluate=graders(task);s=Session(json.loads((td/'task.json').read_text()),work,out/(mode+'-session'),grade,20,2);c=Controller(s)
        def call(name,args):
            r=c.dispatch({'kind':'tool_request','call_id':str(len(c.calls)+1),'name':name,'arguments':json.dumps(args)});c.returned(r['call_id']);return r['observation']
        call('read',{'file':'spec.md'});call('read',{'file':'checker.sv'})
        if mode=='rw':
            first=call('test',{});assert first['status']=='FAIL'
            call('edit',{'file':'checker.sv','content':(td/'reference.sv').read_text()})
            assert first['source_sha256']!=sha(work/'checker.sv')
            assert call('test',{})['status']=='PASS'
            assert call('test',{})['reason']=='test_budget_exhausted'
        call('submit',{});assert call('edit',{'file':'checker.sv','content':'invalid'})['status']=='REJECTED'
        terminal=s.finalize(True);heldout=evaluate(s.out/'submission/checker.sv',out/(mode+'-heldout'))
        expected=1 if mode=='rw' else 0
        assert terminal['reward']==heldout['reward']==expected
        rows.append(dict(task_id=task,accepted=True,actions=s.actions,edits=s.edits,public_tests=s.tests,reward=terminal['reward'],heldout_reward=heldout['reward'],terminal_source_sha256=terminal['source_sha256']))
        save(out/'progress.json',rows)
    result=dict(schema='register-checker-session-acceptance-v1',results=rows,model_calls=0,actual_grader_calls=6,source_sha256=sha(__file__))
    save(out/'result.json',result);return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('out');a=p.parse_args();print(json.dumps(run(a.out),indent=2))
