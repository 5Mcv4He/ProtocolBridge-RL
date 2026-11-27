"""Audit historical simulator logs without treating absent counters as success.

This establishes example-execution evidence, not protocol/Task correctness.
Raw log paths and vendor contents are deliberately excluded from the export.
"""
import argparse,collections,hashlib,json,re
from pathlib import Path

def inspect(data):
    text=data.decode('utf-8',errors='replace')
    counters={kind:[int(x) for x in re.findall(r'^\s*'+kind+r'\s*:\s*(\d+)\s*$',text,re.M)] for kind in ('UVM_ERROR','UVM_FATAL','OVM_ERROR','OVM_FATAL')}
    errors=re.findall(r'^Error-\[([^]]+)\]',text,re.M)
    unsupported='is not supported by this example' in text
    shell_failure='Word too long.' in text
    finished=bool(re.search(r'\$finish at simulation time\s+\d+',text))
    method=next((m for m in ('UVM','OVM') if counters[m+'_ERROR'] and counters[m+'_FATAL']),None)
    if errors:status='compiler_error'
    elif unsupported:status='example_rejected_simulator'
    elif shell_failure:status='build_driver_failure'
    elif not method or not finished:status='incomplete_evidence'
    elif any(counters[method+'_'+kind][-1] for kind in ('ERROR','FATAL')):status='simulation_reports_errors'
    else:status='example_completed_zero_reports'
    return {'log_sha256':hashlib.sha256(data).hexdigest(),'classification':status,'methodology':method,'report_counts':counters,'compiler_error_codes':errors,'finish_seen':finished,'tests':sorted(set(re.findall(r'\+(?:UVM|OVM)_TESTNAME=(\w+)',text))),'task_correctness_established':False,'separate_compile_sim_exit_codes_available':False}

def audit(logdir):
    rows=[dict(suite=p.stem[3:],**inspect(p.read_bytes())) for p in sorted(Path(logdir).glob('mk_*.log'))]
    return {'schema':'vip-example-evidence-audit-v1','rows':rows,'counts':dict(collections.Counter(r['classification'] for r in rows)),'limits':['Make driver exit is not a preserved individual compile/simulation exit status.','Zero report counts and finish establish only example completion, not effective protocol transactions or task validity.','No source or tool upgrade performed by this auditor.']}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('logs');p.add_argument('out');a=p.parse_args();out=Path(a.out)
    if out.exists():raise ValueError('Preserve historical audit')
    out.write_text(json.dumps(audit(a.logs),indent=2)+'\n')
