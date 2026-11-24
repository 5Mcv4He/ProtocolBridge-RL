"""One-way projection. Never forward arbitrary grader strings, nested data or logs."""
import json
from verifier.scenarios import suite

FAILURES={'compile_error','protocol_timing_error','transaction_functional_error','test_timeout'}
CATEGORIES=FAILURES|{'pass','infrastructure_error','invalid_submission'}
CASE_NAMES={c['name'] for c in suite(True,17)}
DIAGNOSTICS={
 'compile_error':'RTL compilation failed.',
 'protocol_timing_error':'A protocol timing or stability requirement failed.',
 'transaction_functional_error':'Transaction mapping, data, response or completion accounting failed.',
 'test_timeout':'The simulation cycle watchdog expired.',
 'infrastructure_error':'Verification did not establish a result.',
 'invalid_submission':'RTL violates the permitted submission language.',
 'pass':'Public verification completed successfully.'}
# Exact trusted messages -> fixed public prose. Arbitrary suffixes are never copied.
TIMING={'AXI acceptance exceeded 16 cycles':'AXI request acceptance exceeded the 16-cycle limit.',
        'Synchronous reset outputs':'Required outputs were not cleared by synchronous reset.'}

def project(result,policy,remaining):
    category=result.get('category')
    if result.get('reward')==1 and category=='pass' and result.get('verification_complete') is True:status='PASS'
    elif result.get('reward')==0 and category in FAILURES:status='FAIL'
    else:status='ENV_ERROR'
    out={'status':status,'remaining_test_calls':remaining}
    if policy['feedback_level']=='diagnostic':
        category=category if category in CATEGORIES else 'infrastructure_error'
        if status=='ENV_ERROR' and category!='invalid_submission':category='infrastructure_error'
        case=result.get('failed_case')
        out.update(category=category,first_failed_case=case if case in CASE_NAMES and status=='FAIL' else None,
                   diagnostic=DIAGNOSTICS[category])
        if status=='FAIL' and category=='protocol_timing_error':
            for c in result.get('cases',[]):
                if c.get('name')==case:
                    for item in c.get('timing_failures',[]):
                        if item in TIMING:out['diagnostic']=TIMING[item];break
                    break
    elif policy['feedback_level']!='verdict':raise ValueError('No test observation allowed')
    if len(json.dumps(out,ensure_ascii=True))>policy['max_feedback_chars']:raise ValueError('Projection exceeds budget')
    return out
