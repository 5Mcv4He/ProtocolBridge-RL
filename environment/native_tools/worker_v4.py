"""One isolated DSH native-tool episode; no evaluator or filesystem tools.

JSONL on the trusted transport carries tool requests/results. A separate local
socket connects only the registered DSH plugin. Native arguments are never
rewritten. Raw runtime events and generated/committed calls are retained.
"""
import argparse,json,os,socket,sys,threading,time,traceback
from dataclasses import asdict
from pathlib import Path
from deepseek_harness import DeepSeekHarness

def main():
    parser=argparse.ArgumentParser();parser.add_argument('work');args=parser.parse_args()
    work=Path(args.work);work.mkdir(parents=True,exist_ok=True)
    initial=json.loads(sys.stdin.readline());key=initial.pop('api_key','')
    output_lock=threading.Lock()
    def emit(value):
        raw=json.dumps(value,ensure_ascii=False)
        if key:raw=raw.replace(key,'[REDACTED]')
        with output_lock:print(raw,flush=True)
    os.environ['DEEPSEEK_API_KEY']=key
    if initial.get('probe_only'):
        status=Path('/proc/self/status').read_text()
        probes={'uid':os.getuid(),'pid':os.getpid(),
                'no_new_privs':next(x.split(':')[1].strip() for x in status.splitlines() if x.startswith('NoNewPrivs:')),
                'cap_eff':next(x.split(':')[1].strip() for x in status.splitlines() if x.startswith('CapEff:')),
                'tmp_canary_absent':not Path('/tmp/pb-native-canary').exists(),
                'host_project_absent':not Path('/home/user/ProtocolBridge-RL').exists(),
                'host_evaluator_absent':not Path('/home/user/work').exists()}
        for name,path in [('worker','/opt/pb/native-tools-v4/worker_v4.py'),('old_worker','/opt/pb/utm_worker.py')]:
            try:
                fd=os.open(path,os.O_WRONLY);os.close(fd);probes[name+'_write_denied']=False
            except PermissionError:probes[name+'_write_denied']=True
        try:os.chroot('/');probes['chroot_denied']=False
        except PermissionError:probes['chroot_denied']=True
        Path('/tmp/pb-native-canary').write_text('private namespace canary')
        emit({'kind':'isolation_probe','checks':probes})
    sock_path=str(work/'controller.sock');ready=work/'tools-ready.json'
    listener=socket.socket(socket.AF_UNIX);listener.bind(sock_path);listener.listen(1);listener.settimeout(.25)
    shutdown=threading.Event();transport_errors=[]
    def serve():
        while not shutdown.is_set():
            try:connection,_=listener.accept()
            except socket.timeout:continue
            except OSError:break
            try:
                connection.settimeout(2520)
                with connection,connection.makefile('rwb') as stream:
                    line=stream.readline(262145)
                    if len(line)>262144 or not line.endswith(b'\n'):raise ValueError('request_limit')
                    packet=json.loads(line);emit(packet)
                    reply_line=sys.stdin.readline(262145)
                    if len(reply_line)>262144:raise ValueError('reply_limit')
                    reply=json.loads(reply_line)
                    if reply.get('call_id')!=packet['call_id']:raise ValueError('reply_identity')
                    stream.write((json.dumps(reply,ensure_ascii=False)+'\n').encode());stream.flush()
            except Exception as error:
                transport_errors.append(type(error).__name__);shutdown.set();emit({'kind':'transport_error','category':type(error).__name__})
    thread=threading.Thread(target=serve,daemon=True);thread.start()
    patch=work/'native-patch.json'
    disabled=[{'id':x,'disabled':True} for x in ('persistent-bash','persistent-pwsh','tool-fs','tool-working-directory','llm-retry')]
    disabled += [{'id':'session-log-deepseek','config':{'enabled':False}},
      {'insert':[{'id':'pb-native-tools','name':'/opt/pb/native-tools-v4/tools_v4.mjs','inject':['tools'],
      'config':{'socket':sock_path,'ready':str(ready),'filename':initial.get('filename','candidate.sv'),'max_model_requests':initial.get('max_model_requests',20),'mechanism_calls':initial.get('mechanism_calls')}}]}]
    patch.write_text(json.dumps(disabled))
    try:
        with DeepSeekHarness(cwd=str(work),dsh_home=str(work/'dsh'),profile='sdk-minimal',provider='deepseek-official',
             model=initial.get('model','deepseek-flash'),reasoning_effort='off',max_tokens=initial.get('max_tokens',1200),
             patches=(str(patch),),request_timeout_seconds=initial.get('timeout_seconds',180)) as harness:
            deadline=time.monotonic()+30
            while not ready.exists() and time.monotonic()<deadline:time.sleep(.05)
            if not ready.exists():
                diagnostics='\n'.join(getattr(harness.client,'_stderr_lines',[]))
                print(diagnostics.replace(key,'[REDACTED]') if key else diagnostics,file=sys.stderr)
            registered=json.loads(ready.read_text())
            if registered['names']!=['edit','read','submit','test']:raise RuntimeError('unexpected_tool_surface')
            emit({'kind':'ready','tools':registered['names'],'uid':os.getuid(),'pid':os.getpid(),
                  'work_siblings':[p.name for p in work.parent.iterdir()]})
            if initial.get('mechanism_calls'):
                emit({'kind':'mechanism_result','result':json.loads(Path(str(ready)+'.mechanism.json').read_text())})
            if not initial.get('probe_only'):
                responses=[]
                def notify(notification):
                    record=asdict(notification)
                    emit({'kind':'notification','notification':record})
                    event=record.get('payload',{}).get('event',{})
                    if event.get('type')=='assistant/message':
                        responses.append(event.get('seq'))
                        if len(responses)>initial.get('max_model_responses',20):
                            raise RuntimeError('model_response_budget')
                try:
                    result=harness.start_session().run(initial['prompt'],on_notification=notify)
                    emit({'kind':'run_result','response':asdict(result)})
                except Exception as error:
                    emit({'kind':'run_error','category':type(error).__name__})
        emit({'kind':'stopped','runtime_closed':True,'transport_errors':transport_errors})
    finally:
        shutdown.set();listener.close();thread.join(timeout=2)

if __name__=='__main__':
    try:main()
    except Exception as error:
        traceback.print_exc(file=sys.stderr)
        print(json.dumps({'kind':'worker_error','category':type(error).__name__}),flush=True)
        raise SystemExit(1)
