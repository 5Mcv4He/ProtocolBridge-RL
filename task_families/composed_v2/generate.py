"""Compose qualified queue/VIP assets with a new finite routing contract.

Generation produces candidates only. Each new mapping requires actual industrial
controls, interaction coverage and source-matched runtime qualification.
"""
import argparse
import json
import shutil
from pathlib import Path
from task_families.capsule import ROOT, finish, write
from task_families.composed_v1.generate import generate as base_generate, TASK as OLD
from .contract import validate, anchors, reset_bins, FAMILY

HERE = Path(__file__).parent


def once(s, old, new):
    if s.count(old) != 1: raise ValueError('Inherited component source changed: ' + old[:65])
    return s.replace(old, new, 1)


def reference_mapping(s, windows):
    functions = '\n function automatic integer decode(input logic [31:0] a);\n'
    for target, (base, size) in enumerate(windows):
        functions += "  if(a>=32'h%x && a<32'h%x) return %d;\n" % (base, base+size, target)
    functions += '  return -1;\n endfunction\n function automatic logic [31:0] local_addr(input logic [31:0] a);\n case(decode(a))\n'
    for target,(base,_) in enumerate(windows):
        functions += "  %d:return a-32'h%x;\n" % (target,base)
    functions += "  default:return 0;\n endcase\n endfunction\n"
    s = once(s, ' state_t state;', ' state_t state;' + functions)
    import re
    s = re.sub(r"\{16'b0,((?:rq|aq)\[\w+\])\[15:0\]\}", r'local_addr(\1)', s)
    s = re.sub(r'((?:rq|aq)\[\w+\])\[31:16\]<3', r'decode(\1)>=0', s)
    s = re.sub(r'((?:rq|aq)\[\w+\])\[31:16\]>=3', r'decode(\1)<0', s)
    s = re.sub(r'((?:rq|aq)\[\w+\]|s_awaddr)\[17:16\]', r'decode(\1)', s)
    return s


def generate(contract, out):
    validate(contract); task_id=contract['task_id']; out=Path(out).resolve()
    base_generate(out)
    (out/'tasks'/OLD).rename(out/'tasks'/task_id)
    for folder in ('tasks','tests','environment','scripts'):
        for p in (out/folder).rglob('*'):
            if p.is_file() and p.suffix in ('.py','.md','.json'):
                s=p.read_text()
                if OLD in s:p.write_text(s.replace(OLD,task_id))
    windows=contract['windows']; task=out/'tasks'/task_id; v=out/'verifier/task003'; fixtures=out/'fixtures/task003'
    for p in fixtures.glob('*.sv'):p.write_text(reference_mapping(p.read_text(),windows))
    oracle='function automatic int expected_target(bit[31:0] a);\n'
    for target,(base,size) in enumerate(windows):
        oracle += " if(a inside {[32'h%x:32'h%x]}) return %d;\n" % (base,base+size-1,target)
    oracle+=' return -1;\nendfunction\nfunction automatic bit[31:0] expected_local(bit[31:0] a);\n case(expected_target(a))\n'
    for target,(base,_) in enumerate(windows):oracle += " %d:return a-32'h%x;\n" % (target,base)
    oracle+=' default:return 0;\n endcase\nendfunction\n'
    vip=v/'vip.sv';s=vip.read_text();old=(ROOT/'task_families/composed_v1/decoder.sv.in').read_text();vip.write_text(once(s,old,oracle))
    points=anchors(contract);write(task/'route-anchors.json',points)
    tb=v/'tb.sv';s=tb.read_text();a=s.index(' initial begin\n  if(expected_target(');b=s.index(' bridge dut',a)
    anchor=' initial begin\n'
    for address,target,offset in points:
        anchor += "  if(expected_target(32'h%x)!=%d || expected_local(32'h%x)!=32'h%x) $fatal(1,\"PB_INFRA: composed byte-ownership anchor mismatch\");\n" % (address,target,address,offset)
    anchor+='  $display("PBX_ORACLE_OK");\n end\n'
    tb.write_text(s[:a]+anchor+s[b:])
    # Actual pins select the phase bin. The declared scenario stage is not used
    # as evidence that the requested lifecycle behavior occurred.
    sb=v/'scoreboard.sv';s=sb.read_text()
    s=once(s,'int id,discarded;bit ew,er,pop_b,pop_r;','int id,discarded,observed_reset_phase;bit ew,er,pop_b,pop_r;')
    hook='''
    if(active && expected_target(expected.addr)>=0) begin
     observed_reset_phase=0;
     if(tb.psel && !tb.penable) observed_reset_phase=tb.pwrite?3:4;
     else if(tb.psel && tb.penable) observed_reset_phase=tb.pwrite?5:6;
     else if(tb.s_bvalid && !tb.s_bready) observed_reset_phase=7;
     else if(tb.s_rvalid && !tb.s_rready) observed_reset_phase=8;
     if(observed_reset_phase) coverage[$sformatf("x_reset_t%0d_s%0d",expected_target(expected.addr),observed_reset_phase)]=1;
    end
'''
    s=once(s,'    discarded=planned-checked-aborted;',hook+'    discarded=planned-checked-aborted;');sb.write_text(s)
    (v/'scenarios.py').rename(v/'_composed_template.py')
    (v/'scenarios.py').write_text((HERE/'scenarios.py.in').read_text().replace('WINDOWS_VALUE',repr(windows)))
    m=json.loads((task/'task.json').read_text());q=m['quality'];controls=q['negative_controls']
    ref=(fixtures/'reference.sv').read_text()
    for target in range(3):
        for stage in range(3,9):
            state='SETUP' if stage<5 else ('ACCESS' if stage<7 else 'RESP')
            direction=1 if stage%2 else 0
            effect='state<='+state+';' if stage<7 else ('s_bvalid<=1;' if direction else 's_rvalid<=1;')
            code='state<=IDLE;if(state==%s && target==%d && pwrite==%d) begin %s end ac<=0;' % (state,target,direction,effect)
            name='bad_reset_t%d_s%d'%(target,stage)
            (fixtures/(name+'.sv')).write_text(once(ref,'state<=IDLE;ac<=0;',code))
            controls.append(dict(source='fixtures/task003/'+name+'.sv',first_case='target_reset_t%d_s%d'%(target,stage),violation='Fails reset cancellation for buffered target %d at observed phase %d'%(target,stage)))
    if any(base%65536 for base,_ in windows):
        bad=ref
        for target,(base,_) in enumerate(windows):
            bad=once(bad,"%d:return a-32'h%x;"%(target,base),"%d:return a & 32'hffff;"%target)
        (fixtures/'bad_window_mask.sv').write_text(bad)
        controls.append(dict(source='fixtures/task003/bad_window_mask.sv',first_case='routed_window_boundaries',violation='Queued target address uses low bits instead of exact base subtraction'))
    m.update(family=dict(contract,version=2,capacity={'aw':2,'w':2,'ar':2}),verifier_revision=3,title='Word-aligned routed retirement queue')
    q['required_cross_bins']=66;q['required_requirements']+=['X_TARGET_RESET_PHASE','X_WINDOW_SUBTRACTION']
    q['minimum_negative_controls']=len(controls)
    q['spec_review']['bounds']='Three word-aligned 64-KiB targets; two unretired credits per AW/W/AR; single retirement-held executor; all target/reset-phase pairs required'
    write(task/'task.json',m)
    obligations=json.loads((task/'obligations.json').read_text())
    obligations.append(dict(id='X_TARGET_RESET_PHASE',kind='capability_interaction',stimulus=['target_reset_t%d_s%d'%(t,s) for t in range(3) for s in range(3,9)],oracle='Buffered request identity plus actual Setup/Access/B-stall/R-stall pins at reset; independent handshake accounting and reset quiescence',coverage=reset_bins(),controls=['bad_reset_t%d_s%d'%(t,s) for t in range(3) for s in range(3,9)]))
    obligations.append(dict(id='X_WINDOW_SUBTRACTION',kind='parameter_interaction',stimulus=['routed_window_boundaries'],oracle='Enumerated byte-ownership anchors plus independent queued transaction/global-to-local comparisons',coverage=[],controls=['bad_window_mask'] if any(b%65536 for b,n in windows) else ['bad_local']))
    write(task/'obligations.json',obligations)
    p=task/'spec.md';s=p.read_text();a=s.index('Address windows (byte addresses, inclusive):');b=s.index('APB PADDR is',a)
    s=s[:a]+'Address windows (byte addresses, inclusive):\n'+''.join('- target %d: 0x%08x..0x%08x.\n'%(i,base,base+size-1) for i,(base,size) in enumerate(windows))+s[b:];p.write_text(s)
    reg=json.loads((out/'tasks/registry.json').read_text());reg['tasks'][0]['title']=m['title'];write(out/'tasks/registry.json',reg)
    p=out/'tests/test_queue003.py';s=p.read_text().replace('len(suite(True)),23','len(suite(True)),42').replace('len(suite()),25','len(suite()),44').replace('len(REQUIRED_BINS),48','len(REQUIRED_BINS),66');p.write_text(s)
    (task/'README.md').write_text('# Routed queue with explicit address windows\n\nRead [the contract](spec.md), [verification obligations](obligations.json) and [independent address anchors](route-anchors.json). Address ownership must survive buffering, arbitration, APB waits and response retirement. Reset coverage requires each target at six observed phases, not merely one reset per target.\n\nGeneration is candidate-only. Actual positive/negative controls and source-matched runtime acceptance are required before Agent sampling.\n')
    (out/'README.md').write_text('# Composed contract candidate\n\nSee [task](tasks/'+task_id+'/README.md). No inherited industrial admission.\n')
    sources=[ROOT/'task_families/capsule.py',ROOT/'task_families/queue_v1/anchor.sv.in']
    sources += [p for directory in (ROOT/'task_families/composed_v1',HERE) for p in directory.iterdir() if p.is_file() and p.suffix in ('.py','.json','.in')]
    # The inherited producer ran tests before specialization. Same-second,
    # same-length source edits can leave timestamp-valid stale bytecode.
    # These caches belong only to this newly created, unadmitted capsule.
    for cache in out.rglob('__pycache__'):
        if cache.is_dir() and not cache.is_symlink():shutil.rmtree(str(cache))
    return finish(out,task_id,FAMILY,contract,sources)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('contract');p.add_argument('out');a=p.parse_args()
    print(generate(json.loads(Path(a.contract).read_text()),a.out)['task_id'])
