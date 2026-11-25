"""Concurrent legal stimulus for independent AW/W/AR credits and serial arbitration.
Rows: write,address,data,strobe,AW/AR-delay,W-delay,APB-wait,response-stall,error,start-delay.
Ordering is defined by actual channel handshakes; SV models queues and memory.
"""
import random
REQUIRED_BINS={'aw_full','w_full','ar_full','aw_ahead','w_ahead','read_write_overlap','both_eligible',
 'read_during_partial_write','intake_during_b_stall','intake_during_r_stall','apb_wait','b_stall','r_stall',
 'read_error','write_error','reset_queued','reset_read_preference'}|{'strobe_%d'%i for i in range(16)}

def suite(public=False,seed=20261125):
    rng=random.Random(seed);cases=[]
    def row(w,a,data=None,st=15,ad=0,wd=0,wait=0,stall=0,err=0,start=0):
        return [w,a,rng.getrandbits(32) if data is None else data,st,ad,wd,wait,stall,err,start]
    def add(name,sequence,rows,req,recovery=None,stage=0,early=False):
        cases.append({'name':name,'sequence':sequence,'rows':rows,'recovery':recovery or [],'reset_stage':stage,
                      'requirements':req,'ready_mode':'early' if early else 'reactive'})
    addresses=[0,4,0xfffffffc,0x80000000]
    add('address_data','queue_memory_sequence',[row(1,a) for a in addresses],['Q_ADDRESS','Q_DATA'],[row(0,a) for a in addresses],early=True)
    n=8 if public else 32
    add('write_fifo','queue_capacity_sequence',[row(1,0x100+(i%4)*4,st=i%16,wait=i%3,stall=4) for i in range(n)],['Q_WRITE_FIFO','Q_AW_CAPACITY','Q_W_CAPACITY','Q_WRAP','Q_STROBE'],[row(0,0x100+i*4) for i in range(4)])
    add('read_fifo','queue_capacity_sequence',[row(0,0x200+i*4,wait=i%5,stall=16) for i in range(n)],['Q_READ_FIFO','Q_AR_CAPACITY','Q_WRAP'])
    for kind in ('b','r'):
        first=int(kind=='b')
        rows=[row(first,0x300,stall=64)]+[row(i%2,0x304+i*4,start=12,wait=2,stall=8) for i in range(7)]
        add('intake_'+kind+'_stall','queue_capacity_sequence',rows,['Q_INTAKE_WHILE_RESPONSE','Q_CAPACITY_CREDIT','Q_'+kind.upper()+'_HOLD'])
    for order in ('aw','w'):
        rows=[row(1,0x400+i*4,ad=64 if order=='w' else 0,wd=64 if order=='aw' else 0,wait=1,stall=8) for i in range(2)]
        rows += [row(0,0x440+i*4,start=8,wait=2,stall=2) for i in range(2)]
        add('partial_'+order,'queue_partial_sequence',rows,['Q_INDEPENDENT_HALVES','Q_READ_DURING_PARTIAL_WRITE'],[row(0,0x400+i*4) for i in range(2)])
    add('round_robin','queue_arbitration_sequence',[row(i%2,0x500+(i%4)*4,wait=3,stall=16) for i in range(12 if public else 32)],['Q_ROUND_ROBIN','Q_SERIAL_EXECUTOR','Q_PAIRING'])
    rows=[row(0,0x600+i*4) for i in range(2)]+[row(i%2,0x640+(i%4)*4,start=32,wait=3,stall=16) for i in range(12)]
    add('preference_history','queue_arbitration_sequence',rows,['Q_ROUND_ROBIN_HISTORY','Q_NO_STARVATION'])
    rows=[row(i%2,0x700+(i%4)*4,st=i%16,wait=i%5,stall=3,err=(i//2)%2) for i in range(16 if public else 64)]
    add('wait_error_memory','queue_memory_sequence',rows,['Q_SELECTED_WAIT','Q_ERROR_RESPONSE','Q_MEMORY_ORDER','Q_ERROR_NO_WRITE'],[row(0,0x700+i*4) for i in range(4)])
    streams=1 if public else 3
    for stream in range(streams):
        rows=[]
        for i in range(12 if public else 64):
            wr=rng.randrange(2);order=rng.randrange(3);delay=rng.choice([1,6,16,31])
            rows.append(row(wr,0x10000+rng.randrange(12)*4,st=rng.randrange(16),ad=delay if order==2 else 0,wd=delay if wr and order==1 else 0,wait=rng.choice([0,1,7,32]),stall=rng.choice([0,1,7,32]),err=rng.randrange(2),start=rng.randrange(5)))
        add('random_%d'%stream,'queue_random_sequence',rows,['Q_RANDOM_INTERLEAVING','Q_LONG_RUN'])
    for stage in range(1,9):
        rows=[row(1,0x800,wait=64 if stage==5 else 0,stall=64),row(1,0x804,stall=64),row(0,0x808,wait=64 if stage==6 else 0,stall=64),row(0,0x80c,stall=64)]
        for i,r in enumerate(rows):
            if stage==1 and r[0]:r[5]=64
            if stage==2 and r[0]:r[4]=64
            if stage==3:
                if not r[0]:r[4]=64
                elif i==1:r[5]=64
            if stage==4:
                if r[0]:r[5]=64
                elif i==3:r[4]=64
            if stage in (5,7) and not r[0]:r[9]=16
            if stage in (6,8):
                if r[0]:r[9]=16
        recovery=[row(0,0x8c0),row(1,0x8c4)]+[row(0,0x800+i*4) for i in range(4)]+[row(1,0x880,data=0x55aa55aa),row(0,0x880)]
        add('reset_%d'%stage,'queue_reset_sequence',rows,['Q_RESET_STAGE_%d'%stage,'Q_RESET_CREDITS','Q_RESET_MEMORY','Q_RESET_PREFERENCE'],recovery,stage)
    return cases
