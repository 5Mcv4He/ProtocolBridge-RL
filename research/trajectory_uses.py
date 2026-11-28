"""Evidence-based research-use candidates. Never reads heldout or offline files.

This is a conservative selection aid, not a training-benefit classifier. Original
rewards remain historical facts even when later verifier defects limit their use.
"""
import argparse,collections,hashlib,json
from pathlib import Path
VERSION='trajectory-use-rules-v1'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def checked(path,digest):
    path=Path(path)
    if sha(path)!=digest:raise ValueError('Source identity mismatch: '+str(path))
    return json.loads(path.read_text())
def inventories(root,inventory,v2_manifest):
    data=json.loads(inventory.read_text());exports=[]
    if 'base_inventory' in data:
        parent=root/data['base_inventory'];checked(parent,data['base_sha256'])
        exports+=inventories(root,parent,v2_manifest)
    elif 'v2_base' in data:
        v=data['v2_base'];validation=checked(root/v['validation'],v['sha256'])
        checked(v2_manifest,validation['manifest_sha256'])
        exports.append((v2_manifest,validation['manifest_sha256']))
    for item in data.get('exports',data.get('additional_exports',[])):
        exports.append((root/item['manifest'],item.get('sha256',item.get('manifest_sha256'))))
    return exports

def load_training(manifest_path,manifest_sha):
    manifest=checked(manifest_path,manifest_sha);base=manifest_path.parent
    name='training/rollouts.jsonl'
    if name not in manifest['files']:raise ValueError('Missing training record dependency')
    p=base/name
    if sha(p)!=manifest['files'][name]:raise ValueError('Training record hash differs')
    rows=[json.loads(x) for x in p.read_text().splitlines() if x]
    if len(rows)!=manifest['records']:raise ValueError('Record count differs')
    def artifacts(value):
        if isinstance(value,dict):
            if 'file' in value and 'sha256' in value and isinstance(value['file'],str) and value['file'].startswith('artifacts/'):
                path=(base/value['file']).resolve()
                if not path.is_relative_to(base.resolve()) or manifest['files'].get(value['file'])!=value['sha256'] or sha(path)!=value['sha256']:
                    raise ValueError('Artifact identity differs')
            for x in value.values():artifacts(x)
        elif isinstance(value,list):
            for x in value:artifacts(x)
    for row in rows:artifacts(row)
    return rows

def analyze(row,manifest_sha,historical_only=False):
    events=row.get('tool_events') or [];outcome=row.get('outcome') or {};resources=row.get('resources') or {}
    final=(row.get('final_submission') or {}).get('sha256');current=None;edits=[];tests=[];rejections=[];issues=[]
    for key,value in (row.get('task_inputs') or {}).items():
        if 'initial' in key and isinstance(value,dict):current=value.get('sha256')
    for e in events:
        a=e.get('action') or {};o=e.get('observation') or {};tool=a.get('tool');index=e['action_index']
        if o.get('status')=='REJECTED':rejections.append({'action':index,'reason':o.get('reason')})
        if not e.get('executed'):continue
        if tool=='read' and o.get('file')!='spec.md':
            h=(o.get('content_artifact') or {}).get('sha256',o.get('content_sha256'))
            if h:
                if current is not None and current!=h:issues.append({'action':index,'reason':'read_binding_differs'})
                current=h
        if tool=='edit':
            h=(a.get('content_artifact') or {}).get('sha256',a.get('content_sha256',o.get('source_sha256')))
            if h is None:issues.append({'action':index,'reason':'edit_hash_missing'})
            edits.append({'action':index,'sha256':h,'changed':h is not None and h!=current});current=h
        if tool=='test' and o.get('status') in ('PASS','FAIL','ENV_ERROR','INVALID'):
            explicit=o.get('source_sha256') or (o.get('candidate_binding') or {}).get('result_sha256')
            if explicit and current and explicit!=current:issues.append({'action':index,'reason':'test_binding_differs'})
            tests.append({'action':index,'sha256':explicit or current,'binding':'explicit' if explicit else 'ordered_trace' if current else 'unknown',
                          'status':o['status'],'delivered':e.get('observation_delivered') is True,'category':o.get('category')})
    final_tests=[t for t in tests if final and t['sha256']==final]
    repairs=[];regressions=[]
    for before in tests:
        for after in tests:
            changed=before['sha256'] and after['sha256'] and before['sha256']!=after['sha256'] and before['action']<after['action']
            edited=any(before['action']<e['action']<after['action'] and e['sha256']==after['sha256'] for e in edits)
            if not changed or not edited:continue
            evidence={'before_action':before['action'],'after_action':after['action'],'before_sha256':before['sha256'],'after_sha256':after['sha256'],
                      'binding':'explicit' if before['binding']==after['binding']=='explicit' else 'ordered_trace'}
            if before['status']=='FAIL' and before['delivered'] and after['status']=='PASS':repairs.append(evidence)
            if before['status']=='PASS' and after['status']=='FAIL':regressions.append(evidence)
    reward=outcome.get('reward');valid=outcome.get('valid_submission',outcome.get('submitted',final is not None)) is True
    infra=outcome.get('infrastructure') is True or outcome.get('category') in ('infrastructure_error','infrastructure_timeout')
    uses=['historical_outcome_analysis']
    if events:uses.append('observed_tool_behavior')
    if rejections or resources.get('protocol_errors',0):uses.append('interaction_failure_analysis')
    if any(t['delivered'] and t['status']=='FAIL' for t in tests):uses.append('failure_feedback_analysis')
    if regressions:uses.append('verified_public_regression_analysis')
    eligible=bool(events and final and valid and reward==1 and not infra and not issues and not historical_only)
    if eligible:uses.append('implementation_demonstration_review')
    repaired_final=[r for r in repairs if r['after_sha256']==final]
    if eligible and repaired_final:uses.append('multi_step_repair_demonstration_review')
    if historical_only:uses.append('superseded_verifier_research_only')
    tokens=resources.get('tokens');tokens=tokens.get('totalTokens') if isinstance(tokens,dict) else tokens
    first=edits[0]['sha256'] if edits else None
    return {'episode_id':row['episode_id'],'task_id':row['task_id'],'manifest_sha256':manifest_sha,
      'cohort':row.get('cohort',row.get('study')),'reward':reward,'terminal_category':outcome.get('category'),
      'valid_submission_reported':valid,'final_source_sha256':final,'final_artifact_available':bool(final),'trajectory_available':bool(events),'historical_only':historical_only,
      'effective_edits':len(edits),'changed_edits':sum(e['changed'] for e in edits),'rejections':rejections,
      'public_tests':tests,'final_public_status':final_tests[-1]['status'] if final_tests else 'not_observed',
      'submitted_known_failed_source':bool(final and any(t['sha256']==final and t['status']=='FAIL' and t['delivered'] for t in tests)),
      'first_edit_final_terminal_pass':bool(first and first==final and valid and reward==1),
      'repair_evidence':repairs,'regression_evidence':regressions,'binding_issues':issues,'potential_uses':uses,
      'cost':{'reported_tokens':tokens,'wall_seconds':resources.get('wall_seconds'),'api_cost':resources.get('api_cost')},
      'limits':['No heldout or posthoc candidate measurement used','Review candidates, not proven training value','Historical terminal reward is not current-source admission']}

def build(root,inventory,v2_manifest):
    root=Path(root);inventory=Path(inventory);seen=set();output=[]
    policy=json.loads(Path(__file__).with_name('trajectory_use_policy_v1.json').read_text())
    if sha(inventory)!=policy['inventory_sha256']:raise ValueError('Inventory requires a new use-policy review')
    checked(root/policy['supersession_notice'],policy['supersession_notice_sha256'])
    superseded_prefixes=set(policy['superseded_task_ids_in_this_inventory'])
    for path,digest in inventories(root,inventory,Path(v2_manifest)):
        for row in load_training(path,digest):
            if row['episode_id'] in seen:raise ValueError('Duplicate episode')
            seen.add(row['episode_id'])
            # This frozen inventory contains only UART verifier1..4 episodes.
            # Do not apply to future inventories without a versioned policy review.
            historical=row['task_id'] in superseded_prefixes
            output.append(analyze(row,digest,historical))
    data=json.loads(inventory.read_text())
    if len(output)!=data['records']:raise ValueError('Inventory denominator mismatch')
    return {'schema':VERSION,'inventory_sha256':sha(inventory),'records':len(output),
      'tool_trajectories':sum(r['trajectory_available'] for r in output),
      'use_counts':dict(collections.Counter(use for r in output for use in r['potential_uses'])),
      'rows':output,'selection_inputs':'training records and existing UART verifier supersession notice only',
      'not_used':['evaluation/','analysis/','heldout outcome','posthoc candidate grades']}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path('.'));p.add_argument('--inventory',type=Path,required=True);p.add_argument('--v2-manifest',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    result=build(a.root,a.inventory,a.v2_manifest)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('x') as f:json.dump(result,f,indent=2,ensure_ascii=False);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
