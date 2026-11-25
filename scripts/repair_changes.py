"""Post-hoc repair-code audit. Token equality is not a general equivalence proof."""
import argparse,difflib,hashlib,json,re
from pathlib import Path

def sha_bytes(b):return hashlib.sha256(b).hexdigest()
def tokens(text):
    # Keep strings and escaped identifiers intact; ignore comments/whitespace.
    # Operators must remain atomic: '< =' is not the token '<='.
    pattern=r'"(?:\\.|[^"\\])*"|/\*.*?\*/|//[^\n]*|\\\S+|===|!==|>>>|<<<|<<|>>|<=|>=|==|!=|&&|\|\||\+\+|--|\*\*|::|->|=>|\w+|[^\s]'
    return [m.group() for m in re.finditer(pattern,text,re.S) if not m.group().startswith(('//','/*'))]

def review(root,out):
    root=Path(root);m=json.loads((root/'experiment.json').read_text());start=(root/'starting.sv').read_bytes()
    if sha_bytes(start)!=m.get('starting_rtl_sha256'):raise ValueError('Repair starting source mismatch')
    rows=[];patches={}
    for item in m['schedule']:
        name=item['id'];d=root/name
        if not (d/'metrics.json').exists():raise ValueError('Complete repair cohort required; do not drop missing trials')
        metrics=json.loads((d/'metrics.json').read_text());trace=json.loads((d/'trace.json').read_text());previous=start.decode();edits=[];first_test=None
        for e in trace:
            a=e['action']
            if e['executed'] and a.get('tool')=='test' and first_test is None:
                first_test={'action_index':e['action_index'],'candidate_sha256':sha_bytes(previous.encode()),'observation':e['observation'],'delivered':e.get('observation_delivered',False),'before_any_edit':not edits}
            if e['executed'] and a.get('tool')=='edit':
                content=a['content'];saved=d/('candidate-%02d.sv'%e['action_index'])
                if saved.read_text()!=content:raise ValueError('Edit source/trace mismatch')
                edits.append({'action_index':e['action_index'],'source_sha256':sha_bytes(content.encode()),'token_changed_from_previous':tokens(content)!=tokens(previous),'token_changed_from_start':tokens(content)!=tokens(start.decode())});previous=content
        final=d/'submission/bridge.sv';same=None
        if final.exists():
            final_hash=sha_bytes(final.read_bytes());graded_hash=metrics['terminal'].get('source_sha256')
            if final_hash!=sha_bytes(previous.encode()) or (graded_hash is not None and final_hash!=graded_hash):raise ValueError('Final source mismatch')
            same=tokens(final.read_text())==tokens(start.decode());patches[name]=''.join(difflib.unified_diff(start.decode().splitlines(True),final.read_text().splitlines(True),fromfile='starting.sv',tofile='submission/bridge.sv'))
        if metrics.get('submitted') and not final.exists():raise ValueError('Submitted source evidence missing')
        initial_fail=bool(first_test and first_test['before_any_edit'] and first_test['candidate_sha256']==m['starting_rtl_sha256'] and first_test['delivered'] and first_test['observation'].get('status')=='FAIL')
        diagnostic=bool(initial_fail and all(k in first_test['observation'] for k in ('category','first_failed_case','diagnostic')))
        rows.append({'trial':name,'policy':item['policy'],'reward':metrics['terminal']['reward'],'initial_failed_feedback_verified':initial_fail,'diagnostic_exposed':diagnostic,'first_test':first_test,'edits':edits,'final_tokens_equal_start':same})
    out=Path(out);out.mkdir(parents=True,exist_ok=False);(out/'patches').mkdir()
    for n,text in patches.items():(out/'patches'/(n+'.diff')).write_text(text)
    result={'analysis':'repair-code-changes-v1','starting_rtl_sha256':m['starting_rtl_sha256'],'code_sha256':sha_bytes(Path(__file__).read_bytes()),'trials':rows,'scope':'Actual delivered first test, exact saved edits and final source. Equal normalized tokens exclude comments/whitespace only; differing tokens do not prove a semantic or useful repair. No candidate or reward is changed.'}
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('out');a=p.parse_args();r=review(a.root,a.out);print(json.dumps({'trials':len(r['trials']),'initial_fail_exposed':sum(x['initial_failed_feedback_verified'] for x in r['trials'])}))
