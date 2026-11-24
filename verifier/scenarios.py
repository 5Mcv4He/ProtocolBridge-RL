"""Requirement-driven stimulus. No expected data comparison is performed here.
Public sample and full regression share requirements; private seeds stay outside Git.
Rows: write,address,data,strobe,AW-delay,W-delay,wait,stall,error,abort-stage,gap.
"""
import random

RESET_STAGES = {'aw_only':1,'w_only':2,'write_setup':3,'read_setup':4,
                'write_wait':5,'read_wait':6,'b_stall':7,'r_stall':8}

def suite(public=False, seed=20261124):
    rng=random.Random(seed)
    cases=[]
    def row(wr, addr, data=None, st=15, ad=0, wd=0, wait=0, stall=0, err=0, abort=0, gap=0):
        return [wr,addr,rng.getrandbits(32) if data is None else data,st,ad,wd,wait,stall,err,abort,gap]
    def pair(rows,addr,**kw):
        rows.append(row(1,addr,**kw));rows.append(row(0,addr,wait=kw.get('wait',0),stall=kw.get('stall',0),err=kw.get('err',0)))
    def add(name,seq,rows,requirements):
        cases.append({'name':name,'sequence':seq,'requirements':requirements,'rows':rows,
                      'ready_mode':'reactive' if any(r[7] for r in rows) else 'early'})
    rows=[]
    patterns=[0,0xffffffff,0xaaaaaaaa,0x55555555] + ([] if public else [1<<i for i in range(32)])
    addresses=[0,4,0xfffffffc,0x80000000] if public else [0,4,0x7ffffffc,0x80000000,0xfffffffc]+[1<<i for i in range(2,32)]
    for i,a in enumerate(addresses):pair(rows,a,data=patterns[i%len(patterns)])
    if not public:
        for data in patterns:pair(rows,0x400,data=data)
    add('address_data','address_data_sequence',rows,['F_ADDR','F_DATA','F_MAPPING'])
    rows=[row(0,a) for a in ([0x44,0x88] if public else [rng.getrandbits(30)*4 for _ in range(24)])]
    add('read_only','memory_pattern_sequence',rows,['F_READ_UNWRITTEN','F_RR'])
    rows=[];a=0x100
    for st in ([1,2,4,8] if public else list(range(16))*2):rows.append(row(1,a,st=st))
    rows += [row(0,a),row(0,a),row(1,a,st=0),row(0,a)]
    add('write_accumulate','memory_pattern_sequence',rows,['F_WW','F_PARTIAL','F_ZERO_STROBE','F_RR'])
    rows=[]
    for st in ([0,1,5,10,15] if public else range(16)):
        for order in (range(1) if public else range(3)):
            for err in range(2):
                for wait in ([1] if public else [0,1,32]):
                    for stall in ([2] if public else [0,33]):
                        pair(rows,rng.getrandbits(30)*4,st=st,ad=6 if order==2 else 0,wd=6 if order==1 else 0,err=err,wait=wait,stall=stall)
    if not public:
        add('strobe_cross_early','strobe_cross_sequence',[r for r in rows if r[7]==0],['F_STROBE_ALL','X_STROBE_ORDER_ERROR_WAIT_STALL'])
        rows=[r for r in rows if r[7]>0]
    add('strobe_cross','strobe_cross_sequence',rows,['F_STROBE_ALL','X_STROBE_ORDER_ERROR_WAIT_STALL'])
    rows=[]
    for delay in ([1,6] if public else [1,2,15,16,31,64]):
        pair(rows,0x200,ad=delay);pair(rows,0x204,wd=delay)
    pair(rows,0x208)
    add('channel_gaps','channel_order_sequence',rows,['F_AW_FIRST','F_W_FIRST','F_TOGETHER','F_HALF_BUFFER'])
    rows=[]
    for wait in ([0,3] if public else [0,1,2,7,16,64]):
        for err in range(2):pair(rows,0x300,wait=wait,err=err)
    add('wait_error','wait_error_sequence',rows,['F_WAIT','F_ERROR_WRITE','F_ERROR_READ','F_ERROR_NO_WRITE'])
    rows=[]
    for stall in ([0,4] if public else [0,1,2,15,16,31,64]):
        for err in range(2):pair(rows,0x500,stall=stall,err=err,wait=2)
    add('response_backpressure','backpressure_sequence',rows,['F_B_STABLE','F_R_STABLE','F_EARLY_READY'])
    rows=[]
    for i in range(12 if public else 128):
        wr=rng.randrange(2);order=rng.randrange(3)
        rows.append(row(wr,rng.randrange(8)*4+0x10000,st=rng.randrange(16),ad=rng.randrange(1,32) if order==2 else 0,wd=rng.randrange(1,32) if order==1 else 0,wait=rng.randrange(17),stall=rng.randrange(17),err=rng.randrange(2),gap=rng.randrange(4)))
    add('mixed_stream','mixed_random_sequence',rows,['F_MIXED','F_STATE_REUSE'])
    if not public:
        # Separate reproducible streams; bias toward boundaries without correlating
        # wait, error, backpressure, strobe and AW/W order with one loop counter.
        for stream in range(4):
            rr=random.Random(seed ^ ((stream+1)*0x9e3779b9))
            rows=[]
            edges=[0,1,2,15,16,31,32,63,64]
            for i in range(256):
                wr=rr.randrange(2) if i%32<16 else (i//16)%2
                order=rr.randrange(3);delay=rr.choice(edges[1:])
                addr=rr.randrange(16)*4+0x20000 if rr.random()<0.75 else rr.getrandbits(30)*4
                rows.append([wr,addr,rr.getrandbits(32),rr.randrange(16),
                             delay if order==2 else 0,delay if order==1 else 0,
                             rr.choice(edges),rr.choice(edges),int(rr.random()<0.25),0,rr.choice([0,0,0,1,7])])
            add('random_stream_%d'%stream,'mixed_random_sequence',rows,['F_RANDOM_LEGAL','F_LONG_RUN','F_INDEPENDENT_PARAMETERS'])
    rows=[]
    for i in range(4 if public else 64):pair(rows,0x800+i*4,wait=0,stall=0)
    add('latency_baseline','address_data_sequence',rows,['F_LATENCY_BASELINE'])
    for name,stage in RESET_STAGES.items():
        rows=[]
        offsets=[0] if public or stage in (3,4) else [0,1,7,31]
        for offset in offsets:
            pair(rows,0x600,data=0x11223344)
            rows.append(row(0 if stage in (4,6,8) else 1,0x600,data=0xdeadbeef,
                            ad=64 if stage==2 else 0,wd=64 if stage==1 else 0,
                            wait=64 if stage in (5,6) else 0,stall=64 if stage in (7,8) else 0,abort=stage+offset*100))
            rows += [row(0,0x600),row(1,0x604,data=0xa5a55a5a),row(0,0x604)]
        add('reset_'+name,'reset_abort_sequence',rows,['F_RESET_'+name.upper(),'F_RESET_RECOVERY'])
    return cases

if __name__=='__main__':
    import json
    print(json.dumps([dict({k:v for k,v in c.items() if k!='rows'},planned=len(c['rows'])) for c in suite()],indent=2))
