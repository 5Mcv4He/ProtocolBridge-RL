"""Fail closed on incomplete tool reports; only known candidate failures get zero."""
import re

def formal(log,rc):
    # The proven boundary has four primary output bits rather than eight.
    # Reuse all strict completeness checks, then adjust only the point minimum.
    from .formal import interpret
    return interpret(log,rc)

def synthesis(log,rc):
    r=dict(reward=None,category='infrastructure_error',verification_complete=False)
    if rc in (124,137):return dict(r,category='infrastructure_timeout')
    if rc or re.search(r'license.*(fail|unavailable)|DCSH-1',log,re.I):return r
    def mark(name):return re.findall(r'^PB_'+name+r'=(\S+)\s*$',log,re.M)
    if 'ELAB-900' in log and mark('ANALYZE')==['1'] and mark('ELABORATE')==['0']:
        return dict(r,reward=0.,category='synthesis_error',reason='data_dependent_loop_not_elaborated')
    if re.search(r'^Error:',log,re.M):return r
    regs=mark('REGISTERS');unmapped=mark('UNMAPPED')
    required=('ANALYZE','LINK','DESIGN','COMPILE','WRITE','DONE')
    if not all(mark(k)==['1'] for k in required) or len(mark('ELABORATE'))!=1 or mark('ELABORATE')==['0']:
        return dict(r,category='incomplete_synthesis')
    if len(regs)!=1 or len(unmapped)!=1 or not regs[0].isdigit() or not unmapped[0].isdigit():return r
    if int(regs[0]) or int(unmapped[0]):return dict(r,reward=0.,category='synthesis_error',reason='noncombinational_or_unmapped_netlist')
    return dict(r,reward=1.,category='pass',verification_complete=True,registers=0,unmapped=0)

def simulation(log,rc,n):
    r=dict(reward=None,category='infrastructure_error',verification_complete=False)
    if rc in (124,137):return dict(r,category='infrastructure_timeout')
    if rc or 'PB_BITFOLD_INFRA' in log:return r
    bad=re.findall(r'^PB_BITFOLD_MISMATCH row=(\d+)\s*$',log,re.M)
    done=re.findall(r'^PB_BITFOLD_COMPLETE rows=(\d+)\s*$',log,re.M)
    if len(bad)==1 and not done:return dict(r,reward=0.,category='transaction_mismatch',first_failure_row=int(bad[0]))
    if done==[str(n)] and not bad:return dict(r,reward=1.,category='pass',verification_complete=True,checked_inputs=n)
    return dict(r,category='missing_activity')
