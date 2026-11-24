"""DSH model worker, executed INSIDE the UTM filesystem/PID sandbox.
Protocol: one bootstrap JSON on stdin, then prompt lines; JSON responses on stdout.
This file contains no grader, reference answer, holdout vectors or EDA credentials.
"""
import argparse,json,os,sys
from dataclasses import asdict
from pathlib import Path
from deepseek_harness import DeepSeekHarness

def main():
    p=argparse.ArgumentParser();p.add_argument('work');a=p.parse_args()
    work=Path(a.work);work.mkdir(parents=True,exist_ok=True)
    initial=json.loads(sys.stdin.readline())
    if initial.get('probe_only'):
        status=Path('/proc/self/status').read_text()
        probes={'uid':os.getuid(),'pid':os.getpid(),'host_home_visible':Path('/home/eda').exists(),
                'host_verifier_visible':Path('/home/eda/work/pb-evaluator').exists(),
                'no_new_privs':next(x.split(':')[1].strip() for x in status.splitlines() if x.startswith('NoNewPrivs:')),
                'effective_capabilities':next(x.split(':')[1].strip() for x in status.splitlines() if x.startswith('CapEff:'))}
        try:os.chroot('/');probes['chroot_escape_denied']=False
        except PermissionError:probes['chroot_escape_denied']=True
        try:
            with open('/opt/pb/utm_worker.py','a'):pass
            probes['worker_write_denied']=False
        except PermissionError:probes['worker_write_denied']=True
        print(json.dumps({'isolation_probe':probes}),flush=True);return
    key=initial.pop('api_key');os.environ['DEEPSEEK_API_KEY']=key
    settings=work/'harness.json'
    settings.write_text(json.dumps([{'id':x,'disabled':True} for x in ('persistent-bash','persistent-pwsh','tool-fs','tool-working-directory','llm-retry')]+[{'id':'session-log-deepseek','config':{'enabled':False}}]))
    with DeepSeekHarness(cwd=str(work),dsh_home=str(work/'dsh'),profile='sdk-minimal',provider='deepseek-official',model=initial.get('model','deepseek-flash'),reasoning_effort='off',max_tokens=7000,patches=(str(settings),),request_timeout_seconds=180) as harness:
        session=harness.start_session()
        for line in sys.stdin:
            request=json.loads(line)
            if request.get('stop'):break
            response=session.run(request['prompt'])
            raw=json.dumps(asdict(response),ensure_ascii=False).replace(key,'[REDACTED]')
            print(json.dumps({'response':json.loads(raw),'worker_pid':os.getpid(),'worker_uid':os.getuid()}),flush=True)

if __name__=='__main__':
    try:main()
    except Exception as e:
        print(json.dumps({'worker_error':type(e).__name__}),flush=True)
        raise SystemExit(1)
