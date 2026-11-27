"""Admitted finite resource tasks; preserves all prior grader contracts."""
import json
from .dispatch_v8 import ROOT,TASKS as PREVIOUS,graders as previous_graders
NEW_TASKS=('fifo_checker_d1_v1','fifo_checker_d5_v1','rffe_register_rw_v1','rffe_register_w1c_v1',
           'bitfold_population_repair_v1','bitfold_trailing_zero_repair_v1','i2c_completion_byte_v1','i2c_completion_word_v1')
TASKS=PREVIOUS+NEW_TASKS

def graders(task):
    if task not in TASKS:raise ValueError('Unknown artifact task')
    if task not in NEW_TASKS:return previous_graders(task)
    if task.startswith('fifo_checker_'):
        from verifier.fifo_checker.campaign_v3 import grade
        from task_families.fifo_checker_v1.qualification_v3 import check
    elif task.startswith('rffe_register_'):
        from verifier.rffe_register.campaign import grade
        from task_families.rffe_register_v1.qualification import check
    elif task.startswith('bitfold_'):
        from verifier.bitfold_synth.campaign import grade
        from task_families.bitfold_synth_v1.qualification import check
    else:
        from verifier.i2c_completion.campaign import grade
        from task_families.i2c_completion_v1.qualification import check
    admission=check(ROOT/'tasks'/task)
    def evaluate(p,o,phase):
        result=grade(task,p,o,phase)
        if task.startswith('bitfold_') and result.get('reward')==1 and result.get('library_sha256')!=admission['library_sha256']:
            # Do not present a result from an unqualified technology model as accepted.
            result.update(reward=None,category='infrastructure_error',verification_complete=False,reason='library_identity_changed')
            from pathlib import Path
            (Path(o)/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        return result
    return (lambda p,o,phase:evaluate(p,o,phase)),(lambda p,o:evaluate(p,o,'evaluation'))

def catalog():return [json.loads((ROOT/'tasks'/t/'task.json').read_text()) for t in TASKS]
