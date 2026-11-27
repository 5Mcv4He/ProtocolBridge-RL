"""Explicit whole-reply rejection feedback; no parser or action repair.

The v1 session/controller remain source-identical for their frozen cohort.
Only rejected format observations receive this additional fixed explanation.
"""
import argparse
from . import runner
from .session import Session,save

class ExplicitRejectionSession(Session):
    def handle(self,action):
        observation=super().handle(action)
        if observation.get('reason')=='invalid_action_format':
            observation['instruction']=('No action from this reply was executed. Return exactly one JSON object, '
                'without prose, fences, or a second action. For an edit, return only '
                '{"tool":"edit","content":"complete file"}; wait for its result before test or submit.')
            save(self.out/'trace.json',self.trace)
        return observation

def run(plan,trial,out):
    original=runner.Session
    try:
        runner.Session=ExplicitRejectionSession
        return runner.run(plan,trial,out)
    finally:runner.Session=original

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('plan');p.add_argument('trial');p.add_argument('out');a=p.parse_args()
    run(a.plan,a.trial,a.out)
