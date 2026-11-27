"""Register behavior is predicted outside the VIP's device memory shadow.

A literal per-bit table defines W1C. Planned readback data are then checked
against both physical serial samples and VIP-observed transactions.
"""
import random


def update(old, data, mode):
    if mode=='rw':return data
    if mode!='w1c':raise ValueError('Unknown register mode')
    table={(0,0):0,(0,1):0,(1,0):1,(1,1):0}
    return sum(table[(old>>i&1,data>>i&1)]<<i for i in range(8))


def corpus(mode,phase):
    if mode not in ('rw','w1c') or phase not in ('public','terminal','evaluation'):raise ValueError('Unknown contract or phase')
    rng=random.Random({'public':1031,'terminal':3079,'evaluation':5011}[phase])
    reset=0 if mode=='rw' else 255
    state=[reset]*16;rows=[]
    def read(a):rows.append((0,a,state[a]))
    def write(a,d):rows.append((1,a,d));state[a]=update(state[a],d,mode)
    for a in range(16):read(a)
    # Read each address independently after values have diverged across the bank.
    for turn in range(2):
        addresses=list(range(16));rng.shuffle(addresses)
        for a in addresses:write(a,((a*73+turn*131)^rng.randrange(256))&255)
        for a in reversed(addresses):read(a)
    rows.append((2,0,0));state[:]=[reset]*16
    for a in range(16):read(a)
    # All bit positions, zero writes, and repeated writes are actual operations.
    for bit in range(8):
        for a in (bit,bit+8):
            write(a,1<<bit);read(a);write(a,0);read(a);write(a,1<<bit);read(a)
    for a in range(16):write(a,255);read(a)
    frames=sum(k!=2 for k,_,_ in rows);reads=sum(k==0 for k,_,_ in rows)
    return rows,{'frames':frames,'reads':reads,'resets':1,'register_addresses':16,
                 'individual_bit_positions':8,'zero_write':True,'repeated_write':True,
                 'address_identity_after_other_writes':True,'read_after_external_idle_reset':True}
