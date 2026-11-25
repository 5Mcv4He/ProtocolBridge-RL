"""Audit and summarize synthesis-profile episodes, without publishing raw logs or inputs."""
import argparse,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.audit_policy import audit
from scripts.batch_analysis import report as batch_report

def report(root):
    root=Path(root);manifest=json.loads((root/'experiment.json').read_text())
    if manifest.get('capabilities')!='synthesis-tools-v1':raise ValueError('Wrong capability contract')
    checked=audit(root)
    if not checked['accepted']:raise ValueError('Episode audit failed; no publishable summary')
    analysis=batch_report(root,len(manifest['schedule']));rows=[]
    for row in analysis['rows']:
        trial=root/row['trial'];metrics=json.loads((trial/'metrics.json').read_text())
        trace=json.loads((trial/'trace.json').read_text());feedback=[];dc_seconds=0
        for event in trace:
            if event['action'].get('tool')!='synth_check' or not event['executed']:continue
            result=json.loads((trial/('synth-%02d'%event['action_index'])/'result.json').read_text())
            dc_seconds+=sum(s['wall_seconds'] for s in result.get('execution',{}).get('stages',[]) if s['stage']=='dc')
            delivered=event.get('observation_delivered',False)
            feedback.append({'action_index':event['action_index'],'source_sha256':result['source_sha256'],
                'delivered':delivered,'observation':event['observation'],
                'later_edits':sum(e['executed'] and e['action'].get('tool')=='edit' and e['action_index']>event['action_index'] for e in trace) if delivered else 0})
        keys=('trial','reward','held_out','effective_edit','submitted','valid_submission','protocol_errors','actions','edits',
              'terminal_category','primary_outcome','public_test_calls','public_verdicts','first_candidate_public','final_candidate_public',
              'feedback','changed_after_failed_feedback','infrastructure','labels',
              'tokens','wall_seconds','model_request_wall_seconds','compile_wall_seconds','simulation_wall_seconds')
        result={k:row.get(k) for k in keys}
        result.update(synth_calls=metrics['synth_calls'],synthesis_feedback=feedback,dc_wall_seconds=round(dc_seconds,4),
                      final_source_sha256=metrics['terminal'].get('source_sha256'),
                      solver_stopped_before_evaluation=metrics['solver_stopped_before_evaluation'])
        rows.append(result)
    return {'schema':'synthesis-study-summary-v1','task_id':manifest['task_id'],'model':manifest['model'],
        'protocol':manifest['protocol'],'capabilities':manifest['capabilities'],'source_commit':manifest['source_commit'],
        'analysis_code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'experiment_sha256':hashlib.sha256((root/'experiment.json').read_bytes()).hexdigest(),
        'toolchain':manifest['toolchain'],'synthesis_binding':manifest['synthesis_binding'],
        'policies':{k:v['sha256'] for k,v in manifest['policies'].items()},
        'suite_hashes':manifest['paired_suite_hashes'],'audit_accepted':checked['accepted'],'rows':rows,
        'groups':analysis['groups'],'quality_gate':analysis['quality_gate'],
        'parameter_training':False,'api_currency_cost':None,
        'limits':['Later edits are temporal association, not evidence of semantic use or successful repair.',
                  'A single capability pilot cannot estimate causal benefit or task difficulty.',
                  'Request time includes API/network/SDK overhead; EDA time includes process startup.',
                  'This research summary is not an extension of the historical training exchange schema.']}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('out');a=p.parse_args()
    value=report(a.root)
    with Path(a.out).open('x') as f:f.write(json.dumps(value,indent=2)+'\n')
