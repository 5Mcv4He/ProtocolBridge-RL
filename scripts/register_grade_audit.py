"""Check source/input/verdict evidence without re-executing EDA or selecting candidates."""
from pathlib import Path
from environment.register_backend_v1 import read, sha, ROOT
from environment.register_inputs_v1 import derive
from task_families.apb_register_v1.campaign import source_policy
from task_families.apb_register_v1.results import simulation_result, compile_result
from task_families.apb_register_v1.verification import config_sv, anchors_sv


def audit_grade(directory, package, trial, role):
    d, p = Path(directory), Path(package)
    r = read(d/'result.json')
    if r['evaluation_role'] != role or r['source_sha256'] != sha(d/'candidate.sv'):
        raise ValueError('Grading role or candidate differs')
    if r['category'] == 'invalid_submission':
        if r['reward'] is not None or not source_policy((d/'candidate.sv').read_text()) or (d/'deployment.json').exists():
            raise ValueError('Unjustified invalid submission')
        return True
    if r['frozen_input_sha256'] != trial['input_sha256'][role] or sha(trial['inputs'][role]) != trial['input_sha256'][role]:
        raise ValueError('Grading input identity differs')
    e = d/'evidence'; g = e/'grade'
    if sha(d/'evidence.tgz') != r['evidence_sha256'] or read(d/'job.json').get('exit_code') != 0:
        raise ValueError('Incomplete grading job')
    c = read(p/'contract.json'); expected = derive(c, trial['seeds'])[role]
    if read(e/'input.json') != expected or read(e/'contract.json') != c:
        raise ValueError('Executed input differs')
    if sha(g/'candidate.sv') != r['source_sha256'] or sha(e/'candidate.sv') != r['source_sha256']:
        raise ValueError('Executed source differs')
    if (sha(g/'tb.sv') != sha(p/'verification/tb.sv') or
            (g/'register_config.svh').read_text() != config_sv(c) or
            (g/'oracle_anchors.svh').read_text() != anchors_sv(c)):
        raise ValueError('Executed checker differs')
    vectors = ''.join('%d %08x %08x %x\n'%tuple(x) for x in expected['vectors'])
    if (g/'vectors.txt').read_text() != vectors or sha(g/'vectors.txt') != r['input_sha256']:
        raise ValueError('Executed vectors differ')
    if r['compile_exit']:
        projected = compile_result((g/'compile.log').read_text(), r['compile_exit'])
    else:
        transfers = sum(x[0] != 2 for x in expected['vectors'])
        resets = 1+sum(x[0] == 2 for x in expected['vectors'])
        projected = simulation_result((g/'simulation.log').read_text(), r['simulation_exit'],
                                      transfers, resets, transfers*c['wait_cycles'], len(c['registers']))
    original = read(g/'result.json')
    for k in ('reward', 'category', 'verification_complete'):
        if r[k] != projected[k] or r[k] != original[k]:
            raise ValueError('Verdict not supported by actual record')
    return True


def grade_cost(path):
    r = read(Path(path)/'result.json')
    return dict(compile_attempts=int('compile_exit' in r),
                simulation_attempts=int('simulation_exit' in r),
                compile_wall_seconds=r.get('compile_wall_seconds'),
                simulation_wall_seconds=r.get('simulation_wall_seconds'),
                grade_wall_seconds=r.get('wall_seconds'),
                scope='Measured subprocess wall time on the licensed host; transfer/collection excluded.')
