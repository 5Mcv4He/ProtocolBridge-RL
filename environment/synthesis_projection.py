"""Allowlisted synthesis observations; trusted formal/teaching metrics stay separate."""
import re
VERSION='synthesis-tools-v1'
WARNINGS={'LINT-1':'Unconnected or unused design connection.',
          'LINT-28':'Design port is not connected to any nets.',
          'LINT-31':'Port or cell connection requires review.',
          'LINT-52':'Constant-driven connection requires review.'}
def markers(log,key):return re.findall(r'^'+re.escape(key)+r'=(\S+)\s*$',log,re.M)
def infra(log,rc):
    return rc!=0 or bool(re.search(r'^Fatal:',log,re.M)) or bool(re.search(r'Unable to.*license|license.*checkout.*fail|cannot.*check.?out|no valid license|license server.*(fail|down)',log,re.I))
def dc_observation(log,rc,netlist):
    out={'status':'ENV_ERROR','diagnostics':[],'functional_correctness_checked':False}
    if infra(log,rc):return out
    errors=[l for l in log.splitlines() if l.startswith('Error:')]
    if markers(log,'PB_ANALYZE')==['0'] and errors and all('bridge.sv' in l for l in errors):
        out.update(status='FAIL',diagnostics=[{'code':'RTL_ANALYSIS','message':'Candidate RTL could not be analyzed.'}]);return out
    if errors or markers(log,'PB_DC_DONE')!=['1'] or markers(log,'PB_COMPILE')!=['1'] or not netlist:return out
    out['status']='PASS'
    latch=markers(log,'PB_LATCHES')
    if len(latch)==1 and latch[0].isdigit() and int(latch[0]):out['diagnostics'].append({'code':'LATCH_INFERRED','message':'Level-sensitive storage was inferred; check whether this is intended.'})
    seen=set()
    for line in log.splitlines():
        if not line.startswith('Warning:'):continue
        codes=re.findall(r'\(([A-Z]+-\d+)\)',line)
        if not codes:continue
        code=codes[-1] if codes[-1] in WARNINGS else 'SYNTH_WARNING'
        if code in seen:continue
        seen.add(code);out['diagnostics'].append({'code':code,'message':WARNINGS.get(code,'Synthesis reported a structural warning; functional correctness is not established.')})
        if len(out['diagnostics'])>=5:break
    return out

def formal_result(log,rc):
    out={'status':'ENV_ERROR','equivalent':None}
    if infra(log,rc) or re.search(r'^Error:',log,re.M):return out
    if markers(log,'PB_EQUIVALENCE')==['1'] and 'Verification SUCCEEDED' in log and any(int(n)>0 for n in re.findall(r'(\d+) Passing compare points',log)):out.update(status='PASS',equivalent=True)
    elif markers(log,'PB_EQUIVALENCE')==['0'] and 'Verification FAILED' in log and any(int(n)>0 for n in re.findall(r'(\d+) Failing compare points',log)):out.update(status='FAIL',equivalent=False)
    return out

def measurement_result(log,rc):
    out={'status':'ENV_ERROR','usable_for_terminal_reward':False,'library_scope':'teaching_relative_only',
         'limitations':['Incomplete teaching-library thresholds and power tables.','Uniform assumed switching activity, not workload-derived activity.']}
    if infra(log,rc):return out
    codes=[]
    for line in log.splitlines():
        if line.startswith('Error:'):
            m=re.search(r'\(([A-Z]+-\d+)\)\s*$',line)
            if m is None or m.group(1)!='DBR-207':return out
            codes.append('DBR-207')
    if markers(log,'PB_PT_DONE')!=['1'] or markers(log,'PB_PT_LINK')!=['1']:return out
    n=markers(log,'PB_PT_PATHS');slack=markers(log,'PB_PT_SLACK')
    if len(n)!=1 or not n[0].isdigit() or int(n[0])<1 or len(slack)!=1:return out
    try:value=float(slack[0])
    except ValueError:return out
    if not (-1e12<value<1e12) or 'Total Power' not in log:return out
    out.update(status='TEACHING_MEASUREMENT',reported_slack=value,known_library_diagnostics=sorted(set(codes)))
    power={}
    for key,label in [('switching','Net Switching Power'),('internal','Cell Internal Power'),('leakage','Cell Leakage Power'),('total','Total Power')]:
        matches=re.findall(r'^\s*'+label+r'\s*=\s*([0-9.eE+-]+)',log,re.M)
        if len(matches)==1:
            try:number=float(matches[0])
            except ValueError:continue
            if 0<=number<1e12:power[key]=number
    out['reported_power']=power
    out['units']={}
    for key,label in [('time','Time_unit'),('internal_power','Internal_power_unit'),('leakage_power','Leakage_power_unit')]:
        matches=re.findall(r'^\s*'+label+r'\s*:\s*([^\n]+)',log,re.M)
        out['units'][key]=matches[0].strip() if len(matches)==1 else None
    out['power_values_scope']='As printed by report_power; not converted to common physical units.'
    out['zero_power_is_not_physical_evidence']=True
    return out

def validate_observation(value):
    """Rebuild from a closed vocabulary; no arbitrary diagnostic strings survive."""
    fallback={'status':'ENV_ERROR','diagnostics':[],'functional_correctness_checked':False}
    if not isinstance(value,dict) or value.get('status') not in ('PASS','FAIL','INVALID','ENV_ERROR'):return fallback
    messages=dict(WARNINGS,RTL_ANALYSIS='Candidate RTL could not be analyzed.',
                  LATCH_INFERRED='Level-sensitive storage was inferred; check whether this is intended.',
                  SYNTH_WARNING='Synthesis reported a structural warning; functional correctness is not established.')
    diagnostics=value.get('diagnostics')
    if not isinstance(diagnostics,list) or len(diagnostics)>5:return fallback
    projected=[]
    for d in diagnostics:
        if not isinstance(d,dict) or d.get('code') not in messages:return fallback
        projected.append({'code':d['code'],'message':messages[d['code']]})
    return {'status':value['status'],'diagnostics':projected,'functional_correctness_checked':False}
