"""New initial material, unchanged independently qualified I2C functional contract."""
import json
from pathlib import Path
from verifier.i2c_sink.campaign import grade as backend_grade,ROOT,sha
from task_families.i2c_sink_v1.qualification import check as backend_admission
TASKS={f'i2c_completion_{m}_v1':m for m in ('byte','word')}

def grade(task,source,out,phase='public'):
    if task not in TASKS:raise ValueError('Unknown completion task')
    backend='i2c_sink_'+TASKS[task]+'_v1'
    backend_admission(ROOT/'tasks'/backend)
    r=backend_grade(backend,source,out,phase)
    r.update(task_id=task,backend_contract_id=backend,adapter_sha256=sha(__file__))
    (Path(out)/'result.json').write_text(json.dumps(r,indent=2)+'\n');return r
