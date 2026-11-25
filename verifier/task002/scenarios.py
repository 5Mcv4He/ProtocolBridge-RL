"""Task002 stimulus: original protocol behaviors plus explicit router requirements.
Python produces stimulus only. SV VIP monitors/scoreboard decide functionality.
"""
import random
from verifier.scenarios import suite as protocol_suite
BASES=(0x1000,0x8000,0x40000000)

def target(a):
    for i,(lo,hi) in enumerate(((0x1000,0x2000),(0x8000,0xa000),(0x40000000,0x40001000))):
        if lo<=a<hi:return i
    return -1

def suite(public=False,seed=20261125):
    cases=protocol_suite(public,seed)
    for c in cases:
        rows=[]
        for r in c['rows']:
            # Preserve same-address dependencies while distributing targets.
            a=r[1];t=(a>>12)%3
            if c['name'].startswith('strobe_cross'):
                for t in range(3):
                    x=list(r);x[1]=BASES[t]+(a&0xffc);rows.append(x)
            else:
                x=list(r);x[1]=BASES[t]+(a&0xffc);rows.append(x)
        c['rows']=rows
    rng=random.Random(seed^0x002ab4)
    def row(wr,a,data=None,st=15,wait=0,stall=0,err=0,ad=0,wd=0,abort=0):
        return [wr,a,rng.getrandbits(32) if data is None else data,st,ad,wd,wait,stall,err,abort,0]
    def add(name,rows,req,sequence='address_data_sequence'):
        cases.append({'name':name,'sequence':sequence,'rows':rows,'requirements':req,'ready_mode':'reactive' if any(r[7] for r in rows) else 'early'})
    rows=[]
    for a in (0x1000,0x1ffc,0x8000,0x8ffc,0x9000,0x9ffc,0x40000000,0x40000ffc):
        rows.extend([row(1,a),row(0,a)])
    add('decode_boundaries',rows,['R_FULL_DECODE','R_LOCAL_ADDRESS','R_TARGET_SELECTION'])
    rows=[]
    misses={0,0xffc,0x2000,0x7ffc,0xa000,0x3ffffffc,0x40001000,0x80001000,0xfffffffc}
    # Every relevant high-address bit must participate in full decoding.
    for base in BASES:
        misses.update(base^(1<<bit) for bit in range(12,32) if target(base^(1<<bit))<0)
    for a in sorted(misses):
        for wr in (0,1):
            rows.append(row(wr,a,wait=0,stall=7,ad=31 if wr else 0))
            rows.extend([row(1,BASES[(a>>2)%3]+4),row(0,BASES[(a>>2)%3]+4)])
    add('decode_misses',rows,['R_DECERR','R_NO_APB_ON_MISS','R_MISS_RECOVERY','F_W_FIRST'])
    rows=[]
    for t in range(3):rows.append(row(0,BASES[t]+0x44))
    for st in ([1,5,15] if public else range(16)):
        for t in range(3):rows.append(row(1,BASES[t]+0x44,st=st,wait=t*3,err=int(st==5)))
        for t in reversed(range(3)):rows.append(row(0,BASES[t]+0x44,wait=2*t,stall=t+1))
    add('independent_target_memory',rows,['R_DISJOINT_MEMORY','R_RESPONSE_MUX','R_TARGET_SWITCH','F_PARTIAL'])
    rows=[]
    for t in range(3):
        for stage in (1,2,3,4,5,6,7,8):
            a=BASES[t]+0x60
            rows.extend([row(1,a,data=0x11223344),row(0,a)])
            rows.append(row(int(stage not in (4,6,8)),a,data=0xdeadbeef,ad=64 if stage==2 else 0,wd=64 if stage==1 else 0,wait=64 if stage in (5,6) else 0,stall=64 if stage in (7,8) else 0,abort=stage))
            rows.extend([row(0,a),row(1,BASES[(t+1)%3]+0x60),row(0,BASES[(t+1)%3]+0x60)])
    for stage in (1,2,7,8):
        rows.append(row(int(stage!=8),0xf000,ad=64 if stage==2 else 0,wd=64 if stage==1 else 0,stall=64 if stage in (7,8) else 0,abort=stage))
        rows.extend([row(0,0xf000),row(1,0x1000),row(0,0x1000)])
    add('router_reset',rows,['R_RESET_EVERY_TARGET','R_UNMAPPED_RESET','R_NO_STALE_ROUTE'],'reset_abort_sequence')
    return cases
