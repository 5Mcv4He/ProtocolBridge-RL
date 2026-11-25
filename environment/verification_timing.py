"""Measure unchanged grader subprocess calls. Never record commands or environments."""
import json,time
from pathlib import Path
import verifier.campaign as campaign

def measured_grade(grader,source,dest,measurement_backend=None,**kwargs):
    backend=campaign if measurement_backend is None else measurement_backend
    original=backend.subprocess;events=[]
    class Proxy:
        def __getattr__(self,name):return getattr(original,name)
        def run(self,args,*a,**kw):
            command=' '.join(str(x) for x in args)
            kind='compile' if 'timeout 1500 vcs ' in command else ('simulate' if 'timeout 600 ./simv ' in command else 'io')
            start=time.monotonic()
            try:return original.run(args,*a,**kw)
            finally:events.append({'kind':kind,'wall_seconds':time.monotonic()-start})
    backend.subprocess=Proxy()
    try:return grader(source,dest,**kwargs)
    finally:
        backend.subprocess=original
        if Path(dest).exists():(Path(dest)/'timing.json').write_text(json.dumps(events,indent=2))
