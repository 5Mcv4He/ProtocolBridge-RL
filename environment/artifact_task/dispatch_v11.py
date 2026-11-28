"""Append finite SWD read transport without changing prior task admission."""
import json
from .dispatch_v10 import ROOT,TASKS as PREVIOUS,graders as previous_graders
TASKS=PREVIOUS+('swd_read_v1',)
def graders(task):
    if task not in TASKS:raise ValueError('Unknown finite task')
    if task!='swd_read_v1':return previous_graders(task)
    from verification_resources.swd_read.qualification import check
    from verifier.swd_read.campaign import grade
    check(ROOT/'tasks'/task)
    return (lambda p,o,phase:grade(task,p,o,phase)),(lambda p,o:grade(task,p,o,'evaluation'))
def catalog():return [json.loads((ROOT/'tasks'/t/'task.json').read_text()) for t in TASKS]
