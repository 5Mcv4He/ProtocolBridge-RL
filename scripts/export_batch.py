"""Publish aggregate study evidence plus explicitly selected, allowlisted trajectories."""
import argparse,hashlib,json,shutil,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.export_policy import export,sha,write


def provenance(source):
    source=Path(source);rows=[]
    for r in json.loads((source/'batch-analysis.json').read_text())['rows']:
        d=source/r['trial'];freeze=json.loads((d/'freeze.json').read_text()) if (d/'freeze.json').exists() else {}
        files=[d/name for name in ('metrics.json','trace.json','freeze.json','observations.json','initial-prompt.txt','policy.json','submission/bridge.sv')]
        files+=list(d.glob('candidate-*.sv'))+list(d.glob('harness-*.json'))
        sessions=set()
        for f in d.glob('harness-*.json'):
            sid=json.loads(f.read_text()).get('response',{}).get('session_id')
            if sid:sessions.add(sid)
        rows.append({'trial':r['trial'],'policy':r['policy'],'repeat':r['repeat'],'reward':r['reward'],
          'session_ids':sorted(sessions),'policy_sha256':freeze.get('policy_sha256'),
          'initial_rtl_sha256':freeze.get('initial_rtl_sha256'),
          'private_reward_suite_sha256':freeze.get('private_reward_suite_sha256'),
          'reserved_evaluation_suite_sha256':freeze.get('reserved_evaluation_suite_sha256'),
          'raw_file_sha256':{str(f.relative_to(d)):sha(f) for f in sorted(files) if f.exists()}})
    return {'scope':'Every started trial; hashes refer to retained original files, not the redacted copies. No raw model text or private inputs included.','trials':rows}



def feedback_history(source):
    source=Path(source);rows=[]
    for r in json.loads((source/'batch-analysis.json').read_text())['rows']:
        d=source/r['trial'];events=[]
        if (d/'trace.json').exists() and (d/'freeze.json').exists():
            active=json.loads((d/'freeze.json').read_text()).get('initial_rtl_sha256')
            for e in json.loads((d/'trace.json').read_text()):
                if e['executed'] and e['action'].get('tool')=='edit':
                    active=hashlib.sha256(e['action']['content'].encode()).hexdigest()
                if e['executed'] and e['action'].get('tool')=='test' and e.get('observation_delivered'):
                    events.append({'action_index':e['action_index'],'candidate_sha256':active,
                        'observation':{k:e['observation'][k] for k in ('status','remaining_test_calls','category','first_failed_case','diagnostic') if k in e['observation']}})
        rows.append({'trial':r['trial'],'policy':r['policy'],'terminal_reward':r['reward'],'delivered_public_tests':events})
    return {'scope':'Only actually delivered public test observations; terminal_reward is research-side data, never solver feedback. Full solver-input audit remains in trusted storage.','trials':rows}


def publish(source,dest,trials):
    source=Path(source);dest=Path(dest)
    analysis=json.loads((source/'batch-analysis.json').read_text())
    # Complete outcome table is always retained; selection only limits large examples.
    # Campaign .cases entries retain the selected runs' complete per-case counts;
    # avoid redundant individual-case and root terminal JSON copies.
    export(source,dest,trials,campaigns_only=True)
    write(dest/'all-trial-provenance.json',provenance(source))
    write(dest/'feedback-history.json',feedback_history(source))
    for name in ('batch-analysis.json','batch-analysis.md','trial-measurements.csv','expansion-decision.json','repair-validity.json','pilot-analysis.json','pilot-analysis.md','pilot-audit.json','eda-resource-analysis.json','quality-stop.json','rtl-failure-analysis.json','repair-review.json'):
        if (source/name).exists():shutil.copyfile(str(source/name),str(dest/name))
    if (source/'starting.sv').exists():shutil.copyfile(str(source/'starting.sv'),str(dest/'starting.sv'))
    for name in trials:
        patch=source/'patches'/(name+'.diff')
        if patch.exists():
            (dest/'patches').mkdir(exist_ok=True)
            shutil.copyfile(str(patch),str(dest/'patches'/patch.name))
        for p in (source/name).rglob('timing.json'):
            entries=json.loads(p.read_text())
            write(dest/name/p.relative_to(source/name),[{k:e[k] for k in ('kind','wall_seconds') if k in e} for e in entries])
    resources=[json.loads(p.read_text()) for p in source.glob('r*-resources.json')]
    if resources:
        write(dest/'resource-summary.json',{'samples':len(resources),'concurrent_trials':1,
              'minimum_free_disk_bytes':min(x['free_disk_bytes'] for x in resources),
              'maximum_loadavg_1m':max(x['loadavg'][0] for x in resources),
              'logical_cpus':sorted(set(x['cpus'] for x in resources)),
              'scope':'Between-trial snapshots, not peak memory/CPU or monetary billing.'})
    write(dest/'publication.json',{'format':'batch-selected-allowlist-v1','all_started_trials':len(analysis['rows']),
         'selected_trajectories':trials,'selection_does_not_change_denominators':True,
         'raw_evidence':'Full model/EDA logs and private inputs retained in trusted local storage, not published.',
         'files':{str(p.relative_to(dest)):sha(p) for p in sorted(dest.rglob('*')) if p.is_file() and p.name!='publication.json'}})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('dest');p.add_argument('--trials',required=True);a=p.parse_args();publish(a.source,a.dest,a.trials.split(','))
