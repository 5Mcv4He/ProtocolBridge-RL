"""Append bounded structural measurement feedback only for the admitted budget task."""
import json
from .session_v4 import Session as Previous,save
VERSION="engineering-artifact-session-v6"

def project_measurement(value):
    # Explicit whitelist; private logs/paths and arbitrary additional result keys
    # cannot enter the observation. No coercion of strings or bool-as-int.
    if not isinstance(value,dict) or value.get('metric_version')!='dc-mapped-instance-count-v1':raise ValueError('Unknown metric')
    count=value.get('mapped_cell_count');limit=value.get('limit')
    if type(count)!=int or not 0<=count<=1000000 or type(limit)!=int or limit!=22 or value.get('functional_checks_passed') is not True:raise ValueError('Invalid metric')
    return {'mapped_cell_count':count,'limit':limit,'functional_checks_passed':True}

class Session(Previous):
    def __init__(self,task,work,out,grader,max_actions=20,max_tests=4):
        self.last_grade=None
        def captured(candidate,dest,phase):
            r=grader(candidate,dest,phase);self.last_grade=r;return r
        super().__init__(task,work,out,captured,max_actions,max_tests)
        p=self.out/"session.json";record=json.loads(p.read_text());record["version"]=VERSION;save(p,record)
    def handle(self,action):
        self.last_grade=None;obs=super().handle(action)
        if (self.task['task_id']=='bitfold_cell_budget_v1' and self.last_grade is not None
            and obs.get('status') in ('PASS','FAIL') and 'resource_measurement' in self.last_grade):
            try:obs['measurement']=project_measurement(self.last_grade['resource_measurement'])
            except ValueError:obs.update(status='ENV_ERROR',category='infrastructure_error')
            save(self.out/'trace.json',self.trace)
        return obs
