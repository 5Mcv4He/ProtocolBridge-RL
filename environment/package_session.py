"""Native single-artifact session for qualified router packages, version 1.

The router's explicit in-simulation progress watchdog is a bounded contract
violation. A process/SSH timeout remains infrastructure failure. Historical
artifact sessions and their classifications are unchanged.
"""
import json
from environment.artifact_task.session_v4 import Session as Previous,save
VERSION='qualified-router-session-v1'

class Session(Previous):
    def __init__(self,task,work,out,grader,max_actions=20,max_tests=4):
        self.last_grade=None
        def captured(candidate,dest,phase):
            r=grader(candidate,dest,phase);self.last_grade=r;return r
        super().__init__(task,work,out,captured,max_actions,max_tests)
        p=self.out/'session.json';m=json.loads(p.read_text());m['version']=VERSION;save(p,m)

    def handle(self,action):
        self.last_grade=None;obs=super().handle(action)
        if (self.last_grade is not None and self.last_grade.get('reward')==0
                and self.last_grade.get('category')=='test_timeout'):
            obs.update(status='FAIL',category='test_timeout')
            save(self.out/'trace.json',self.trace)
        return obs
