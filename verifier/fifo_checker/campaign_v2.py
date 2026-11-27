"""VCS evaluates the submitted checker; a trusted deque supplies expected verdicts.

No candidate-supplied assertions, vectors, commands or score aggregation execute
on the trusted side. Candidate RTL uses the existing restricted-source boundary.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import time
import uuid
from environment.remote_backend import remote_command
from verifier.independent_formal.campaign import ROOT, sha, source_policy as rtl_policy
from verifier.uart_tx.campaign_v4 import classify_compile
from .model_v2 import corpus

TASKS = {'fifo_checker_d2_v1': 2, 'fifo_checker_d3_v1': 3}


def source_policy(text):
    invalid = rtl_policy(re.sub(r'\bmodule\s+fifo_checker\b', 'module accumulator', text, count=1))
    if invalid:
        return invalid
    clean = re.sub(r'/\*.*?\*/|//[^\n]*', ' ', text, flags=re.S)
    if '#' in clean:
        return 'delay_or_parameter_not_supported'
    header = re.search(r'\bmodule\s+fifo_checker\s*\((.*?)\)\s*;', clean, re.S)
    if not header:
        return 'fixed_ansi_interface_required'
    expected = [('clk', 'input', 1), ('rst_n', 'input', 1), ('push', 'input', 1),
                ('pop', 'input', 1), ('push_id', 'input', 8), ('pop_id', 'input', 8),
                ('error', 'output', 1)]
    actual = []
    direction, width = None, 1
    for port in header[1].split(','):
        d = re.search(r'\b(input|output|inout)\b', port)
        if d:
            direction, width = d[1], 1
        bounds = re.search(r'\[\s*(\d+)\s*:\s*(\d+)\s*\]', port)
        if bounds:
            width = abs(int(bounds[1]) - int(bounds[2])) + 1
        elif '[' in port:
            return 'literal_interface_width_required'
        words = re.findall(r'[A-Za-z_][A-Za-z_0-9]*', re.sub(r'\[[^\]]*\]', '', port))
        actual.append((words[-1] if words else None, direction, width))
    return None if actual == expected else 'fixed_interface'


def bench():
    return '''`timescale 1ns/1ps
module tb;
  bit clk=0;always #5 clk=~clk;
  bit rst_n,push,pop;bit [7:0] push_id,pop_id;wire error;
  integer f,n,r,a,b,c,d,e,expected;integer cases=0;
  fifo_checker dut(.clk(clk),.rst_n(rst_n),.push(push),.pop(pop),
    .push_id(push_id),.pop_id(pop_id),.error(error));
  initial begin
    f=$fopen("events.txt","r");
    if(!f)begin $display("PB_CHECKER_INFRA missing_vectors");$finish;end
    r=$fscanf(f,"%d\\n",n);
    if(r!=1 || n<1)begin $display("PB_CHECKER_INFRA invalid_count");$finish;end
    for(integer i=0;i<n;i=i+1)begin
      @(negedge clk);r=$fscanf(f,"%d %d %d %d %d %d\\n",a,b,c,d,e,expected);
      if(r!=6)begin $display("PB_CHECKER_INFRA incomplete_vectors");$finish;end
      rst_n=a;push=b;pop=c;push_id=d;pop_id=e;
      @(posedge clk);#1;
      if(error!==expected[0])begin
        $display("PB_CHECKER_MISMATCH row=%0d expected=%0d observed=%0b",i,expected,error);$finish;
      end
      cases++;
    end
    $display("PB_CHECKER_COMPLETE rows=%0d",cases);$finish;
  end
  initial begin #1000000;$display("PB_CHECKER_INFRA watchdog");$finish;end
endmodule
'''


def interpret(log, rc, count):
    if rc in (124, 137):
        return dict(reward=None, category='infrastructure_timeout', verification_complete=False)
    if rc or 'PB_CHECKER_INFRA' in log:
        return dict(reward=None, category='infrastructure_error', verification_complete=False)
    bad = re.findall(r'^PB_CHECKER_MISMATCH row=(\d+) expected=([01]) observed=([01xz])\s*$', log, re.M)
    done = re.findall(r'^PB_CHECKER_COMPLETE rows=(\d+)\s*$', log, re.M)
    if len(bad) == 1 and not done:
        return dict(reward=0., category='transition_mismatch', verification_complete=False,
                    first_mismatch=dict(row=int(bad[0][0]), expected=int(bad[0][1]), observed=bad[0][2]))
    if not bad and done == [str(count)]:
        return dict(reward=1., category='pass', verification_complete=True, checked_cycles=count)
    return dict(reward=None, category='missing_activity', verification_complete=False)


def grade(task, source, out, phase='public'):
    if task not in TASKS:
        raise ValueError('Unregistered checker task')
    rows, coverage = corpus(TASKS[task], phase)
    out, source = Path(out).resolve(), Path(source)
    out.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    result = dict(task_id=task, phase=phase, source_sha256=sha(source),
                  grader_sha256=sha(__file__), verifier_revision=2, model_sha256=sha(Path(__file__).with_name('model_v2.py')),
                  reward=None, category='infrastructure_error', verification_complete=False)
    try:
        invalid = source_policy(source.read_text())
        if invalid:
            result.update(category='invalid_submission', reason=invalid)
            return result
        (out / 'candidate.sv').write_bytes(source.read_bytes())
        (out / 'tb.sv').write_text(bench())
        (out / 'events.txt').write_text(str(len(rows)) + '\n' + '\n'.join(' '.join(map(str, row)) for row in rows) + '\n')
        result['input_sha256'] = sha(out / 'events.txt')
        result['planned_event_obligations'] = coverage
        cfg = json.loads(Path(os.environ.get('PB_CONFIG', ROOT / '.local/config.json')).read_text())
        ssh = ['ssh', '-F', cfg['ssh_config'], cfg['host']]
        remote = cfg['remote_root'] + '/fifo-checker-' + uuid.uuid4().hex

        def run(command, timeout):
            return subprocess.run(ssh + [remote_command(cfg, command)], capture_output=True, text=True, timeout=timeout)

        setup = run('mkdir -p ' + shlex.quote(remote), 30)
        if setup.returncode:
            return result
        subprocess.run(['scp', '-F', cfg['ssh_config']] + [str(out / f) for f in
                       ('candidate.sv', 'tb.sv', 'events.txt')] + [cfg['host'] + ':' + remote + '/'],
                       check=True, capture_output=True, timeout=30)
        (out / 'deployment.json').write_text(json.dumps({'remote': remote}))
        t = time.monotonic()
        c = run('cd ' + shlex.quote(remote) + ' && timeout 120 vcs -full64 -sverilog -timescale=1ns/1ps candidate.sv tb.sv -top tb -o simv', 150)
        result.update(compile_exit=c.returncode, compile_seconds=round(time.monotonic()-t, 4))
        (out / 'compile.log').write_text(c.stdout + c.stderr)
        if c.returncode:
            if classify_compile(c.stdout+c.stderr) == 'compile_error':
                result.update(reward=0., category='compile_error')
            return result
        t = time.monotonic()
        s = run('cd ' + shlex.quote(remote) + ' && timeout 10 ./simv', 30)
        result.update(simulation_exit=s.returncode, simulation_seconds=round(time.monotonic()-t, 4))
        (out / 'simulation.log').write_text(s.stdout+s.stderr)
        result.update(interpret(s.stdout+s.stderr, s.returncode, len(rows)))
        if result['reward'] == 1:
            result['executed_event_obligations'] = coverage
        result['simulation_sha256'] = sha(out / 'simulation.log')
    except subprocess.TimeoutExpired:
        result['category'] = 'infrastructure_timeout'
    except Exception as exc:
        result['exception_type'] = type(exc).__name__
    finally:
        result['wall_seconds'] = round(time.monotonic()-start, 4)
        (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('task', choices=TASKS)
    p.add_argument('source')
    p.add_argument('out')
    p.add_argument('--phase', default='public')
    a = p.parse_args()
    print(json.dumps(grade(a.task, a.source, a.out, a.phase), indent=2))
