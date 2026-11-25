"""Check published aggregate arithmetic from all-trial measurements; no private logs needed."""
import argparse,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.batch_analysis import interval
from scripts.batch_tables import aggregate


def check(root):
    root=Path(root);data=json.loads((root/'batch-analysis.json').read_text());results={}
    for policy,g in data['groups'].items():
        rows=[r for r in data['rows'] if r['policy']==policy];n=len(rows);k=sum(r['reward']==1 for r in rows)
        assert g['started']==n and g['successes']==k,policy
        assert g['wilson95']==interval(k,n),policy
        assert g['reward_distribution']=={('null' if v is None else str(v)):sum(r['reward']==v for r in rows) for v in (0,1,None)},policy
        assert g['measurements']==aggregate(rows),policy
        for field,c in g['conditional'].items():
            subset=[r for r in rows if r.get(field)];success=sum(r['reward']==1 for r in subset)
            assert c['n']==len(subset) and c['successes']==success and c['wilson95']==interval(success,len(subset)),(policy,field)
        results[policy]={'started':n,'successes':k,'wilson95':interval(k,n)}
    if (root/'publication.json').exists():
        for name,digest in json.loads((root/'publication.json').read_text())['files'].items():
            assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
    if (root/'all-trial-provenance.json').exists():
        manifest=json.loads((root/'experiment.json').read_text())
        evidence=json.loads((root/'all-trial-provenance.json').read_text())['trials']
        assert len(evidence)==len(data['rows']) and len({e['trial'] for e in evidence})==len(evidence)
        sessions=set()
        for e in evidence:
            row=next(r for r in data['rows'] if r['trial']==e['trial'])
            assert e['reward']==row['reward'] and e['policy']==row['policy'] and e['repeat']==row['repeat']
            assert not sessions.intersection(e['session_ids']),e['trial']
            sessions.update(e['session_ids'])
            pair=manifest['paired_suite_hashes'][str(e['repeat'])]
            assert e['private_reward_suite_sha256']==pair['reward'],e['trial']
            assert e['reserved_evaluation_suite_sha256']==pair['evaluation'],e['trial']
            assert e['policy_sha256']==manifest['policies'][e['policy']]['sha256'],e['trial']
    if (root/'feedback-history.json').exists():
        history=json.loads((root/'feedback-history.json').read_text())['trials']
        assert len(history)==len(data['rows']) and len({e['trial'] for e in history})==len(history)
        for e in history:
            row=next(r for r in data['rows'] if r['trial']==e['trial'])
            assert e['terminal_reward']==row['reward'] and e['policy']==row['policy']
            events=e['delivered_public_tests']
            assert bool(any(x['observation']['status'] in ('PASS','FAIL') for x in events))==row['feedback']
            assert len(events)<=row.get('public_test_calls',0),e['trial']
            for x in events:
                fields={'status','remaining_test_calls'}
                if e['policy']=='test_diagnostic':fields|={'category','first_failed_case','diagnostic'}
                assert set(x['observation'])==fields,e['trial']
    return {'public_summary_consistency':True,'scope':'Published arithmetic, file hashes and declared input/session/feedback linkage; not a full raw-trajectory audit or RTL replay.','groups':results}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root');a=p.parse_args();print(json.dumps(check(a.root),indent=2))
