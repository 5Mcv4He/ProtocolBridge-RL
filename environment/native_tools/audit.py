"""Check native generation, host execution and actual SDK feedback independently."""
import hashlib,json

def audit(events,calls,requests,submitted):
    sdk=[r['notification']['payload']['event'] for r in events
         if r.get('kind')=='notification' and r['notification']['method']=='session.event']
    generated=[];results=[];submitted_at=None
    for event in sdk:
        if event['type']=='assistant/message':
            for block in event['data']['message']['content']:
                if block['type']=='tool-call':generated.append((block['id'],block['name'],block['arguments']))
        elif event['type']=='tool/result':
            m=event['data']['message'];text=''.join(b['text'] for b in m['content'] if b['type']=='text')
            results.append((m['toolCallId'],hashlib.sha256(text.encode()).hexdigest()))
    dispatched=[(r['request']['call_id'],r['request']['name'],r['raw_arguments']) for r in calls]
    if generated!=dispatched:raise ValueError('Generated/dispatched calls differ')
    expected=[(r['request']['call_id'],r['observation_text_sha256']) for r in calls]
    if results!=expected:raise ValueError('Actual SDK feedback differs from allowed observation')
    if len({r[0] for r in generated})!=len(generated):raise ValueError('Duplicate generated identity')
    for r in calls:
        if submitted_at is not None and r['executed']:raise ValueError('Operation executed after submission')
        if r['observation'].get('status')=='SUBMITTED':submitted_at=r['action_index']
    if submitted!=(submitted_at is not None):raise ValueError('Submission state differs')
    if submitted and calls[-1]['model_receipt_confirmed']:raise ValueError('Feedback after submission')
    responses=[e for e in sdk if e['type']=='assistant/message']
    if len(responses)!=sum(r['response_received'] for r in requests):raise ValueError('Unmatched responses')
    return {'schema':'native-action-audit-v2','accepted':True,'generated_calls':len(generated),
            'executed_operations':sum(r['executed'] for r in calls),'sdk_results':len(results),
            'observations_in_completed_model_requests':sum(r['model_receipt_confirmed'] for r in calls),
            'model_responses':len(responses),'submitted':submitted}
