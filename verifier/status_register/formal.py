"""Independent-reference status-register equivalence; full eight-bit comparison."""
import re
def interpret(log,rc):
    result={'reward':None,'category':'infrastructure_error','equivalent':None,'verification_complete':False,'exit_code':rc}
    def marker(k):return re.findall(r'^'+k+r'=(\S+)\s*$',log,re.M)
    if rc in (124,137):result['category']='proof_timeout';return result
    if rc or re.search(r'license.*(fail|unavailable)|cannot.*check.?out',log,re.I):return result
    if marker('PB_REFERENCE_READ')!=['1'] or marker('PB_REFERENCE_TOP')!=['1']:return result
    if marker('PB_CANDIDATE_READ')==['0'] or marker('PB_CANDIDATE_TOP')==['0']:
        result.update(reward=0.0,category='compile_error');return result
    if re.search(r'^Error:',log,re.M) or marker('PB_REFERENCE_DONE')!=['1']:return result
    if "No 'black boxes' matched current 'reference and implementation designs'" not in log:
        result['category']='incomplete_comparison';return result
    unmatched=re.findall(r'(\d+)\((\d+)\) Unmatched reference\(implementation\) (compare points|primary inputs, black-box outputs)',log)
    if not unmatched or any(int(a) or int(b) for a,b,_ in unmatched):
        result['category']='incomplete_comparison';return result
    passed=[int(x) for x in re.findall(r'(\d+) Passing compare points',log)]
    failed=[int(x) for x in re.findall(r'(\d+) Failing compare points',log)]
    result.update(passing_points=passed[-1] if passed else 0,failing_points=failed[-1] if failed else 0)
    complete=all(x in log for x in ('No unverified compare points.','No aborted compare points.'))
    if marker('PB_REFERENCE_EQ')==['0'] and 'Verification FAILED' in log and result['failing_points']>0:
        result.update(reward=0.0,category='not_equivalent',equivalent=False)
    elif marker('PB_REFERENCE_EQ')==['1'] and 'Verification SUCCEEDED' in log and result['passing_points']>=8 and not result['failing_points'] and complete and 'No failing compare points.' in log:
        result.update(reward=1.0,category='pass',equivalent=True,verification_complete=True)
    else:result['category']='incomplete_comparison'
    return result

