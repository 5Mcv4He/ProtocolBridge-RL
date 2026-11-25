"""Publish aggregate study evidence plus explicitly selected, allowlisted trajectories."""
import argparse,json,shutil,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.export_policy import export,sha,write


def publish(source,dest,trials):
    source=Path(source);dest=Path(dest)
    analysis=json.loads((source/'batch-analysis.json').read_text())
    # Complete outcome table is always retained; selection only limits large examples.
    export(source,dest,trials)
    for name in ('batch-analysis.json','batch-analysis.md','trial-measurements.csv','expansion-decision.json','repair-validity.json','pilot-analysis.json','pilot-analysis.md','pilot-audit.json'):
        if (source/name).exists():shutil.copyfile(str(source/name),str(dest/name))
    if (source/'starting.sv').exists():shutil.copyfile(str(source/'starting.sv'),str(dest/'starting.sv'))
    for name in trials:
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
