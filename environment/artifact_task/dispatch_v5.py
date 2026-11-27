"""Explicit finite task adapters. No Agent-selected module import or command."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
TASKS=('accumulator_wrap_repair_v1','accumulator_saturating_repair_v1','uart_tx_8n1_v1','uart_tx_8e1_v1','x2p_stimulus_mapping_v1','x2p_stimulus_timing_v1')
def graders(task):
 if task not in TASKS:raise ValueError('Unknown artifact task')
 if task.startswith('accumulator_'):
  from verifier.independent_formal.campaign import grade
  from verifier.independent_formal.anchor import run
  return (lambda p,o,phase:grade(task,p,o)),(lambda p,o:run(task,p,o))
 if task.startswith('uart_'):
  from verifier.uart_tx.campaign_v5 import grade
 else:
  from verifier.stimulus.campaign import grade
 return (lambda p,o,phase:grade(task,p,o,phase)),(lambda p,o:grade(task,p,o,'evaluation'))
def catalog():
 return [json.loads((ROOT/'tasks'/t/'task.json').read_text()) for t in TASKS]
