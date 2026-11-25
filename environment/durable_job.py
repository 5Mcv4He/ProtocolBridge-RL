"""Trusted detached single-job supervisor; credentials only ever travel in memory."""
import json,os,subprocess,sys,time
from pathlib import Path

def atomic(path,value):
    p=Path(path);tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2));os.replace(str(tmp),str(p))

def main():
    request=json.loads(sys.stdin.readline());name=request['name']
    if not name.replace('-','').replace('_','').isalnum():raise ValueError('Invalid job name')
    folder=Path('.jobs')/name;folder.parent.mkdir(exist_ok=True)
    try:folder.mkdir()
    except FileExistsError:
        print('EXISTS',flush=True);return
    pid=os.fork()
    if pid:
        print('STARTED',flush=True);return
    os.setsid()
    log=os.open(str(folder/'controller.log'),os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o600)
    null=os.open('/dev/null',os.O_RDONLY)
    os.dup2(null,0);os.dup2(log,1);os.dup2(log,2)
    started=time.time();atomic(folder/'state.json',{'pid':os.getpid(),'started':started,'status':'running','proc_start':Path('/proc/self/stat').read_text().split()[21] if Path('/proc/self/stat').exists() else None})
    result={'status':'finished','started':started}
    try:
        p=subprocess.run([sys.executable,'-m',request['module']]+request['args'],input=json.dumps(request.get('bootstrap',{}))+'\n',universal_newlines=True)
        result['exit_code']=p.returncode
    except Exception as e:result.update(exit_code=None,error_type=type(e).__name__)
    result['ended']=time.time();atomic(folder/'state.json',result)
    os._exit(0)
if __name__=='__main__':main()
