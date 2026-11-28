"""Independent state as per-address sets of asserted bits, not RTL word updates."""
import random
MODES=('rw','w1c')

def annotate(events,mode):
    if mode not in MODES:raise ValueError('Unsupported contract')
    state=[set() for _ in range(16)];failed=False;rows=[]
    coverage={k:0 for k in ('reset','reset_active','legal_read','write','bad_read','sticky','idle','idle_valid_looking_write','idle_bad_read','ignored_write_payload','ignored_read_payload','back_to_back','read_after_write','repeat_read')}
    written=set();last=None;last_address=None
    address_bits=set();written_addresses=set();bad_addresses=set()
    for event in events:
        if len(event)!=6 or any(type(x)!=int for x in event):raise ValueError('Invalid event')
        rst,valid,write,addr,data,seen=event
        if rst not in (0,1) or valid not in (0,1) or write not in (0,1) or not 0<=addr<16 or not 0<=data<256 or not 0<=seen<256:raise ValueError('Event outside contract')
        if not rst:
            state=[set(range(8)) if mode=='w1c' else set() for _ in range(16)];failed=False;written.clear()
            coverage['reset']+=1;coverage['reset_active']+=valid;last=None
        elif failed:coverage['sticky']+=1
        elif not valid:
            coverage['idle']+=1;coverage['idle_valid_looking_write']+=write
            expected=sum(2**b for b in state[addr]);coverage['idle_bad_read']+=not write and seen!=expected;last=None
        else:
            coverage['back_to_back']+=last is not None
            if write:
                active={b for b in range(8) if (data//(2**b))%2}
                if mode=='rw':state[addr]=active
                else:state[addr].difference_update(active)
                coverage['write']+=1;coverage['ignored_read_payload']+=seen!=0;written.add(addr);written_addresses.add(addr)
            else:
                expected=sum(2**b for b in state[addr]);failed=seen!=expected
                coverage['bad_read']+=failed;coverage['legal_read']+=not failed
                coverage['ignored_write_payload']+=data!=0
                coverage['read_after_write']+=addr in written
                coverage['repeat_read']+=last==0 and last_address==addr
                if failed:
                    bad_addresses.add(addr)
                    for bit in range(8):
                        if (seen//2**bit)%2 != (expected//2**bit)%2:address_bits.add((addr,bit))
            last=write;last_address=addr
        rows.append(list(event)+[int(failed)])
    coverage.update(written_addresses=len(written_addresses),bad_read_addresses=len(bad_addresses),bad_address_bit_pairs=len(address_bits))
    return rows,coverage

def anchors():
    # Literal examples reviewed independently of the scenario producer and RTL.
    w1c=[[0,1,1,3,255,0],[1,1,0,3,0,255],[1,1,1,3,1,0],[1,1,1,3,2,0],[1,1,0,3,0,252],[1,1,1,3,2,0],[1,1,0,3,0,252],[1,1,0,2,0,255],[1,1,0,3,0,254],[1,0,0,0,0,0],[0,1,1,3,255,0],[1,1,0,3,0,255]]
    rw=[[0,0,0,0,0,0],[1,1,1,9,165,255],[1,0,1,9,0,0],[1,1,0,9,255,165],[1,1,1,9,90,0],[1,1,0,9,0,90],[1,1,0,1,0,0],[1,1,0,9,0,91],[1,1,0,9,0,90],[0,1,1,9,1,0],[1,1,0,9,0,0]]
    for mode,events,expected in [('w1c',w1c,[0]*8+[1,1,0,0]),('rw',rw,[0]*7+[1,1,0,0])]:
        if [r[-1] for r in annotate(events,mode)[0]]!=expected:raise ValueError('Independent literal anchor failed')
    return {'w1c_literal_cycles':len(w1c),'rw_literal_cycles':len(rw)}

def corpus(mode,phase):
    if mode not in MODES or phase not in ('public','terminal','evaluation'):raise ValueError('Unknown input domain')
    anchors();rng=random.Random({'public':811,'terminal':1777,'evaluation':2909}[phase]);ev=[]
    reset_value=0 if mode=='rw' else 255
    def reset():ev.append([0,1,1,rng.randrange(16),rng.randrange(256),0])
    def write(a,v,valid=1):ev.append([1,valid,1,a,v,rng.randrange(1,256)])
    def read(a,v,valid=1):ev.append([1,valid,0,a,rng.randrange(1,256),v])
    addresses=list(range(16));rng.shuffle(addresses)
    for addr in addresses:
        for bit in range(8):
            reset();read(addr,reset_value)
            write(addr,1<<bit);value=(1<<bit) if mode=='rw' else 255-(1<<bit)
            read(addr,value);read(addr,value)
            # Touch every other address while preserving selected state.
            for other in addresses:
                if other!=addr:read(other,reset_value)
            write(addr,255,0);read(addr,value^255,0);read(addr,value)
            write(addr,1<<bit);read(addr,value) # idempotence or overwrite
            read(addr,value^(1<<bit));read(addr,value);write(addr,0);read(addr,0)
            reset();read(addr,reset_value)
    # Independent legal-sequence builder uses byte arithmetic; oracle uses sets.
    for epoch in range(8):
        reset();state=[reset_value]*16
        for _ in range(80):
            a=rng.randrange(16)
            if rng.randrange(2):
                v=rng.choice([0,255,rng.randrange(256)]);write(a,v)
                state[a]=v if mode=='rw' else state[a] & (255^v)
            else:read(a,state[a])
        a=rng.randrange(16);read(a,state[a]^128);read(a,state[a]);reset();read(a,reset_value)
    rows,coverage=annotate(ev,mode)
    if not all(coverage.values()) or coverage['written_addresses']!=16 or coverage['bad_read_addresses']!=16 or coverage['bad_address_bit_pairs']!=128:raise ValueError('Required observed event missing')
    return rows,coverage
