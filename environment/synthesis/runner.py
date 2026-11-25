"""Trusted remote runner. Fixed files/tools only; no solver-provided commands."""
import hashlib,json,os,re,subprocess,time
from pathlib import Path

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def binding():
    lib=Path(os.environ['CLASS_DB']);env=Path(os.environ['PB_EDA_ENV_SCRIPT'])
    return {'library_sha256':digest(lib),'library_path':str(lib.resolve()),'environment_script_sha256':digest(env),'environment_script_path':str(env.resolve())}
def main():
    request=json.loads(Path('request.json').read_text());before=binding();rows=[]
    for name,tool,script,budget in [('dc','dc_shell','dc.tcl',180),('fm','fm_shell','fm.tcl',120),('pt','pt_shell','pt.tcl',90)]:
        if name=='fm' and not request['equivalence']:continue
        if name=='pt' and not request['measure']:continue
        if name!='dc' and not Path('mapped.v').exists():break
        start=time.monotonic()
        with Path(name+'.log').open('wb') as log:
            args=['timeout','-k','5',str(budget),tool]+(['-64bit'] if name=='fm' else [])+['-f',script]
            try:rc=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=budget+10).returncode
            except Exception:rc=125
        text=Path(name+'.log').read_text(errors='replace')
        versions=re.findall(r'\b(?:O|V|R|N|K)-\d{4}\.\d{2}(?:-SP\d+)?\b',text)
        rows.append({'stage':name,'exit_code':rc,'wall_seconds':round(time.monotonic()-start,4),'tool_version':versions[0] if versions else None})
        # Stop on failed/unclassified stage; never spend additional licenses on it.
        from projection import dc_observation,formal_result,measurement_result
        text=Path(name+'.log').read_text(errors='replace')
        status=(dc_observation(text,rc,Path('mapped.v').exists())['status'] if name=='dc' else formal_result(text,rc)['status'] if name=='fm' else measurement_result(text,rc)['status'])
        if status not in ('PASS','TEACHING_MEASUREMENT'):break
    after=binding()
    Path('execution.json').write_text(json.dumps({'binding_before':before,'binding_after':after,'stages':rows},indent=2)+'\n')
if __name__=='__main__':main()
