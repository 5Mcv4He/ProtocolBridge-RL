"""Derived measurements from immutable rollout artifacts; no API or simulation."""
import argparse,hashlib,json
from pathlib import Path

FIELDS=('inputTokens','outputTokens','cacheReadTokens','cacheWriteTokens','totalTokens')

def usage(files):
    seen=set();turns=[]
    for p in sorted(files):
        message=json.loads(p.read_text())['response'];sid=message['session_id']
        for event in message.get('events',[]):
            if event['type']!='assistant/message' or 'usage' not in event.get('data',{}):continue
            key=(sid,event['seq'])
            if key in seen:continue
            seen.add(key);values=event['data']['usage']
            turns.append({'event_file':p.name,'event_seq':event['seq'],'usage':{k:values.get(k) for k in FIELDS}})
    if not turns:return {'available':False,'totals':None,'cost':None,'events':[]}
    totals={k:sum(t['usage'][k] for t in turns) if all(isinstance(t['usage'][k],(int,float)) for t in turns) else None for k in FIELDS}
    return {'available':True,'totals':totals,'cost':None,'events':turns,
            'method':'Sum unique (session_id, seq) assistant/message.data.usage events only; exclude stream chunks and duplicated notifications.',
            'semantics':'SDK inputTokens excludes separately reported cacheReadTokens in these records; totalTokens is the SDK total, not unique context size. No billed currency cost is provided.'}


def analyze(root):
    root=Path(root);manifest=json.loads((root/'experiment.json').read_text());runs=[]
    for trial in manifest['schedule']:
        path=root/trial['id']
        if not (path/'metrics.json').exists():continue
        metrics=json.loads((path/'metrics.json').read_text())
        trace=json.loads((path/'trace.json').read_text()) if (path/'trace.json').exists() else []
        u=usage(list(path.glob('harness-*.json')))
        (path/'usage-derived.json').write_text(json.dumps(u,indent=2))
        runs.append({'trial':trial['id'],'policy_id':metrics['policy_id'],'actions':metrics['actions'],'edits':metrics['edits'],
            'rejected_actions':sum(not e['executed'] for e in trace),'public_test_calls':metrics['public_test_calls'],
            'public_feedback':[{'action_index':e['action_index'],'delivered':e.get('observation_delivered',False),'observation':e['observation']} for e in trace if e['action'].get('tool')=='test' and e['executed']],
            'terminal':metrics['terminal'],'held_out':metrics['held_out'],'first_candidate_public':metrics['first_candidate_public'],
            'final_candidate_public':metrics['final_candidate_public'],'wall_seconds':metrics['wall_seconds'],
            'usage':u,'raw_metrics_sha256':hashlib.sha256((path/'metrics.json').read_bytes()).hexdigest()})
    report={'kind':'derived_analysis','runs':runs,'parameter_training':False,'planned_repeats':manifest['repeats']}
    (root/'analysis.json').write_text(json.dumps(report,indent=2));return report
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source');a=p.parse_args();r=analyze(a.source)
    print(json.dumps([{'trial':x['trial'],'usage':x['usage']['totals'],'wall_seconds':x['wall_seconds']} for x in r['runs']],indent=2))
