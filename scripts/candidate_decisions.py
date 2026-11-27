"""Analyze observed candidate/test decisions, never infer unmeasured correctness."""
import hashlib,json
from pathlib import Path

def sha_text(text):return hashlib.sha256(text.encode()).hexdigest()
def analyze(episode):
    d=Path(episode);freeze=json.loads((d/'freeze.json').read_text());metrics=json.loads((d/'metrics.json').read_text())
    trace=json.loads((d/'trace.json').read_text());current=freeze['initial_rtl_sha256']
    versions=[{'action':0,'sha256':current,'kind':'start'}];tests=[];edits=[];public_by_source={};pass_seen=False;edits_after_pass=[];development=[]
    for e in trace:
        a=e['action'];o=e['observation'];tool=a.get('tool');index=e['action_index']
        if not e['executed']:continue
        if tool=='edit':
            before=current;current=sha_text(a['content'])
            row={'action':index,'before_sha256':before,'source_sha256':current,'changed_bytes':before!=current}
            edits.append(row);versions.append({'action':index,'sha256':current,'kind':'edit'})
            if pass_seen:edits_after_pass.append(index)
        elif tool=='test':
            b=o.get('candidate_binding')
            if b is not None and (b['current_sha256']!=current or b['result_sha256']!=current):raise ValueError('Public test source mismatch')
            row={'action':index,'source_sha256':current,'status':o['status'],'delivered':e.get('observation_delivered',False),'ordinal':len(tests)+1}
            tests.append(row);public_by_source.setdefault(current,[]).append(row)
            if row['delivered'] and row['status']=='PASS':pass_seen=True
        if tool in ('test','experiment','compile','synth_check','inspect','observe'):
            result_source=o.get('candidate_binding',{}).get('result_sha256',current)
            development.append({'action':index,'tool':tool,'source_sha256':result_source,'status':o.get('status'),'delivered':e.get('observation_delivered',False),'new_execution':tool not in ('inspect','observe')})
    for row in edits:
        later=[x for x in tests if x['action']>row['action'] and x['source_sha256']==row['source_sha256']]
        # Querying inspect/observe is not another test of the edited candidate.
        row['later_public_test_actions']=[x['action'] for x in later]
        row['prior_public_test_actions']=[x['action'] for x in tests if x['action']<row['action'] and x['source_sha256']==row['source_sha256']]
    final_file=d/'submission/bridge.sv';final_sha=hashlib.sha256(final_file.read_bytes()).hexdigest() if final_file.exists() else None
    if final_sha is not None and final_sha!=current:raise ValueError('Final source is not active candidate')
    matching=public_by_source.get(final_sha,[]);delivered=[x for x in matching if x['delivered']]
    budget=freeze['policy']['max_public_test_calls'];outcome=metrics['terminal']
    regressions=[]
    for prev,nxt in zip(tests,tests[1:]):
        if prev['status']=='PASS' and nxt['status']=='FAIL' and prev['source_sha256']!=nxt['source_sha256']:
            regressions.append({'passing_action':prev['action'],'failing_action':nxt['action'],'scope':'same frozen public suite; no inference about untested candidates'})
    return {'schema':'candidate-verification-decisions-v1','budget':budget,'actions':metrics['actions'],'submitted':metrics['submitted'],
        'submission_validity':('not_submitted' if not metrics['submitted'] else 'invalid' if outcome.get('category')=='invalid_submission' else 'confirmed' if outcome.get('reward') in (0,1) else 'unresolved'),'terminal':outcome,'held_out':metrics.get('held_out'),'initial_source_sha256':freeze['initial_rtl_sha256'],
        'final_source_sha256':final_sha,'versions':versions,'edits':edits,'public_tests':tests,
        'extra_public_tests_used':sum(x['ordinal']>2 for x in tests),'unused_test_allowance':budget-len(tests),
        'conflicting_public_verdict_sources':[h for h,xs in public_by_source.items() if {'PASS','FAIL'}<={x['status'] for x in xs}],
        'final_public_status':('NOT_SUBMITTED' if final_sha is None else matching[-1]['status'] if matching else 'UNTESTED'),
        'final_delivered_public_status':('NOT_SUBMITTED' if final_sha is None else delivered[-1]['status'] if delivered else 'UNOBSERVED'),
        'submitted_previously_failed_source':bool(delivered and delivered[-1]['status']=='FAIL'),
        'known_failure_definition':'Identical final source with latest delivered full-public-test verdict FAIL; local experiment evidence is listed separately.',
        'final_development_evidence':[x for x in development if x['source_sha256']==final_sha],
        'final_delivered_functional_failure_tools':sorted({x['tool'] for x in development if x['source_sha256']==final_sha and x['delivered'] and x['status']=='FAIL' and x['tool'] in ('test','experiment')}),
        'edited_after_delivered_pass':edits_after_pass,'observed_public_regressions':regressions,
        'untested_edit_versions':sum(not x['later_public_test_actions'] for x in edits),
        'untested_edit_versions_definition':'Edit actions without a later full public test of that source; an identical earlier tested source can still have known evidence.',
        'never_publicly_tested_edited_sources':sorted({x['source_sha256'] for x in edits}-{x['source_sha256'] for x in tests}),
        'offline_first_candidate':metrics.get('first_candidate_public'),
        'limits':'Untested does not mean incorrect. Same SHA is identity, not correctness. Private/held-out outcomes never select intermediate candidates. Submit motives are not observable from atomic action replies.'}
