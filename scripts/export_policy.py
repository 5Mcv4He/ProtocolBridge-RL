"""Allowlist export of policy experiments; raw API/EDA events and inputs stay local."""
import argparse,hashlib,json,shutil
from collections import Counter
from pathlib import Path


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def compact_result(r):
    keys=('reward','category','verification_complete','verdict_determinate','source_sha256','suite_sha256','required_cases','planned','checked','aborted','functional_cross','failed_case','compile_exit','compile_reused')
    out={k:r[k] for k in keys if k in r}
    out['cases']=[{k:c[k] for k in ('name','reward','category','planned','expected_aborted','scoreboard','routing','simulation_exit','requirements') if k in c} for c in r.get('cases',[])]
    return out

def export(source,dest,trial_ids=None,campaigns_only=False):
    source=Path(source);dest=Path(dest);dest.mkdir(parents=True,exist_ok=False)
    manifest=json.loads((source/'experiment.json').read_text())
    selected=None if trial_ids is None else set(trial_ids)
    if selected is not None and not selected.issubset({x['id'] for x in manifest['schedule']}):
        raise ValueError('Selected trial is not in the frozen schedule')
    for name in ('experiment.json','summary.json','analysis.json','audit.json'):
        shutil.copyfile(str(source/name),str(dest/name))
    if (source/'runtime-probe.json').exists():
        shutil.copyfile(str(source/'runtime-probe.json'),str(dest/'runtime-probe.json'))
    if (source/'bringup.json').exists():
        shutil.copyfile(str(source/'bringup.json'),str(dest/'bringup.json'))
    write(dest/'mechanism/result.json',json.loads((source/'mechanism/result.json').read_text()))
    for p in (source/'mechanism').rglob('result.json'):
        if p==source/'mechanism/result.json':continue
        value=json.loads(p.read_text())
        if campaigns_only and 'cases' not in value:continue
        write(dest/p.relative_to(source),compact_result(value))
    write(dest/'mechanism/raw-evidence-sha256.json',{
        str(p.relative_to(source/'mechanism')):sha(p)
        for p in sorted((source/'mechanism').rglob('*')) if p.is_file()})
    for item in manifest['schedule']:
        name=item['id'];src=source/name
        if selected is not None and name not in selected:continue
        if not (src/'metrics.json').exists():continue
        dst=dest/name;dst.mkdir()
        for f in ('metrics.json','freeze.json','policy.json','initial-prompt.txt'):
            shutil.copyfile(str(src/f),str(dst/f))
        if (src/'usage-derived.json').exists():
            shutil.copyfile(str(src/'usage-derived.json'),str(dst/'usage-derived.json'))
        for p in list(src.glob('candidate-*.sv'))+list((src/'submission').glob('bridge.sv')):
            q=dst/p.relative_to(src);q.parent.mkdir(exist_ok=True);shutil.copyfile(str(p),str(q))
        trace=json.loads((src/'trace.json').read_text()) if (src/'trace.json').exists() else []
        for event in trace:
            action=event['action']
            if 'content' in action:
                content=action.pop('content')
                payload=content if isinstance(content,str) else json.dumps(content,sort_keys=True)
                action['content_sha256']=hashlib.sha256(payload.encode()).hexdigest()
                candidate='candidate-%02d.sv'%event['action_index']
                action['candidate_file']=candidate if event['executed'] and (src/candidate).exists() else None
            obs=event['observation']
            if 'content' in obs:
                content=obs.pop('content');obs['content_sha256']=hashlib.sha256(content.encode()).hexdigest();obs['content_bytes']=len(content.encode())
        write(dst/'trace.json',trace)
        # Exact serialized prompts kept locally. Hashes permit matching each sent
        # observation; public test observations above are unchanged, not re-projected.
        observations=json.loads((src/'observations.json').read_text()) if (src/'observations.json').exists() else []
        write(dst/'observation-provenance.json',[{'turn':x['turn'],'prompt_sha256':hashlib.sha256(x['prompt'].encode()).hexdigest(),'prompt_bytes':len(x['prompt'].encode())} for x in observations])
        events=[]
        for p in sorted(src.glob('harness-*.json')):
            r=json.loads(p.read_text());response=r['response']
            events.append({'file':p.name,'sha256':sha(p),'worker_uid':r['worker_uid'],'worker_pid':r['worker_pid'],
                           'session_id':response.get('session_id'),'event_types':dict(Counter(e['type'] for e in response.get('events',[]))),
                           'request_headers':[{k:v for k,v in e['data'].get('header',{}).get('config',{}).items()
                                               if k in ('maxTokens','provider','model','reasoningEffort')}
                                              for e in response.get('events',[]) if e['type']=='request/header']})
        write(dst/'harness-provenance.json',events)
        for p in src.rglob('result.json'):
            value=json.loads(p.read_text())
            if campaigns_only and ('cases' not in value or p.parent==src):continue
            write(dst/p.relative_to(src),compact_result(value))
        if (src/'first-candidate-result.json').exists():write(dst/'first-candidate-result.json',compact_result(json.loads((src/'first-candidate-result.json').read_text())))
        write(dst/'raw-evidence-sha256.json',{str(p.relative_to(src)):sha(p) for p in sorted(src.rglob('*')) if p.is_file()})
    write(dest/'publication.json',{'format':'policy-allowlist-v1','selected_trials':None if selected is None else sorted(selected),'raw_evidence':'Retained locally; no private vectors, commercial logs, API keys or full model responses published.',
         'files':{str(p.relative_to(dest)):sha(p) for p in sorted(dest.rglob('*')) if p.is_file()}})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('dest');p.add_argument('--trials',help='Comma-separated selected trajectories; aggregate denominators remain complete');a=p.parse_args();export(a.source,a.dest,None if a.trials is None else a.trials.split(','))
