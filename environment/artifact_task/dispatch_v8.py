"""Add finite I2C write sinks without changing prior task contracts or grading."""
import json
from .dispatch_v7 import ROOT,TASKS as PREVIOUS,graders as previous_graders
TASKS=PREVIOUS+('i2c_sink_byte_v1','i2c_sink_word_v1')
def graders(task):
    if task not in TASKS:raise ValueError('Unknown artifact task')
    if task.startswith('i2c_sink_'):
        from verifier.i2c_sink.campaign import grade
        from task_families.i2c_sink_v1.qualification import check
        check(ROOT/'tasks'/task)
        return (lambda p,o,phase:grade(task,p,o,phase)),(lambda p,o:grade(task,p,o,'evaluation'))
    return previous_graders(task)
def catalog():return [json.loads((ROOT/'tasks'/t/'task.json').read_text()) for t in TASKS]
