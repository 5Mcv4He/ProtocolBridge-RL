"""Strict, dependency-free policy contract (JSON; Python 3.6 compatible)."""
import hashlib,json
from pathlib import Path

POLICIES=Path(__file__).resolve().parent/'policies'
FIELDS={'policy_id','version','allowed_tools','readable_files','writable_files',
        'feedback_level','max_agent_actions','max_public_test_calls','max_feedback_chars',
        'final_reward_visibility','submission_requirements'}

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)

def policy_hash(policy):
    return hashlib.sha256(canonical(policy).encode()).hexdigest()

def validate(p):
    if not isinstance(p,dict) or set(p)!=FIELDS:raise ValueError('Invalid policy fields')
    if p['policy_id'] not in ('spec_only','test_verdict','test_diagnostic'):raise ValueError('Unknown policy')
    if type(p['version']) is not int or p['version']!=1:raise ValueError('Unsupported policy version')
    a=p['policy_id']=='spec_only'
    expected={'read','edit','submit'} | (set() if a else {'test'})
    if not isinstance(p['allowed_tools'],list) or len(p['allowed_tools'])!=len(expected) or set(p['allowed_tools'])!=expected:raise ValueError('Invalid tools')
    if p['readable_files']!=['spec.md','bridge.sv'] or p['writable_files']!=['bridge.sv']:raise ValueError('Invalid file boundary')
    level={'spec_only':'none','test_verdict':'verdict','test_diagnostic':'diagnostic'}[p['policy_id']]
    if p['feedback_level']!=level:raise ValueError('Invalid feedback level')
    for key,value in [('max_agent_actions',20),('max_public_test_calls',0 if a else 2),('max_feedback_chars',512)]:
        if type(p[key]) is not int or p[key]!=value:raise ValueError('Invalid budget: '+key)
    if p['final_reward_visibility']!='none':raise ValueError('Terminal reward is not an observation')
    if p['submission_requirements']!={'read_spec_and_rtl':True,'public_test_required':False} or any(type(v) is not bool for v in p['submission_requirements'].values()):raise ValueError('Invalid submission requirements')
    return p

def load(name):
    path=POLICIES/(name+'.json')
    if name not in ('spec_only','test_verdict','test_diagnostic'):raise ValueError('Unknown policy')
    def unique(pairs):
        out={}
        for k,v in pairs:
            if k in out:raise ValueError('Duplicate policy field')
            out[k]=v
        return out
    return validate(json.loads(path.read_text(),object_pairs_hook=unique))

def prompt(p):
    # C/E deliberately have identical prompts. Policy identifiers are not disclosed.
    tools=['{"tool":"read","file":"spec.md"}', '{"tool":"read","file":"bridge.sv"}',
           '{"tool":"edit","content":"complete RTL"}']
    if 'test' in p['allowed_tools']:tools.append('{"tool":"test"}')
    tools.append('{"tool":"submit"}')
    return ('Implement the RTL task. Return exactly one JSON object per turn. Allowed actions: '+', '.join(tools)+
        '. Read both files before editing or submitting. Submit even if public tests fail; public testing is optional. '+
        'You have at most 20 actions and %d public test invocations. Every started test, including ENV_ERROR, consumes one invocation. '%p['max_public_test_calls']+
        'Final verification is private and its feedback is unavailable. Only spec.md and bridge.sv can be read; only bridge.sv can be edited. '+
        'Do not access other files, hierarchy, simulator system tasks or external includes.')
