"""Fail-closed result projection for the finite APB register checker."""
import re
# Same conservative attribution rule used by the qualified UART compile path.
# Kept source-local so a generated register package needs no UART runtime.
def classify_compile(log):
    errors=re.findall(r'Error-\[.*?(?=\nError-|\Z)',log,re.S)
    infra=re.search(r'(?:license|licensing)[^\n]*(?:fail|unavailable|denied|error)|cannot[^\n]*check.?out|cannot find',log,re.I)
    return 'compile_error' if errors and all('candidate.sv' in e[:400] for e in errors) and not infra else 'infrastructure_error'



def compile_result(log,rc):
    if rc==0:return dict(reward=None,category='compiled_not_verified',verification_complete=False)
    category=classify_compile(log)
    return dict(reward=0.0 if category=='compile_error' else None,category=category,verification_complete=False)


def simulation_result(log,rc,transfers,resets,waits,registers):
    if any(type(x)!=int or x<0 for x in (transfers,resets,waits,registers)) or not transfers or not resets or not 2<=registers<=4:
        raise ValueError('Explicit bounded activity expectations required')
    result=dict(reward=None,category='infrastructure_error',verification_complete=False)
    if rc in (124,137):return dict(result,category='infrastructure_timeout')
    if 'PB_INFRA' in log or re.search(r'(?:license|licensing)[^\n]*(?:fail|unavailable|denied)|cannot[^\n]*check.?out',log,re.I):return result
    if '[PB_TIMING]' in log:return dict(result,reward=0.,category='protocol_timing_error')
    if '[PB_FUNCTION]' in log:return dict(result,reward=0.,category='transaction_functional_error')
    if re.search(r'UVM_(?:ERROR|FATAL)[^\n]*\[register_fail:AMBA:',log):return dict(result,reward=0.,category='protocol_timing_error')
    if 'PB_REGISTER_TIMEOUT' in log:
        return dict(result,reward=0.,category='test_timeout') if 'PB_REGISTER_ACTIVITY' in log else result
    done=re.findall(r'^PB_REGISTER_DONE checked=(\d+) resets=(\d+) waits=(\d+)$',log,re.M)
    coverage=re.findall(r'^PB_REGISTER_COVERAGE observed=(\d+) required=(\d+)$',log,re.M)
    if rc or len(done)!=1 or len(coverage)!=1 or log.count('PB_ORACLE_ANCHORS_OK')!=1:return result
    if not re.search(r'UVM_ERROR\s*:\s*0',log) or not re.search(r'UVM_FATAL\s*:\s*0',log):return result
    if tuple(map(int,done[0]))!=(transfers,resets,waits) or tuple(map(int,coverage[0]))!=(17*registers,17*registers):
        return dict(result,category='incomplete_verification')
    return dict(result,reward=1.,category='pass',verification_complete=True,
                checked=transfers,resets=resets,waits=waits,observed_bins=17*registers)
