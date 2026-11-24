"""Stimulus only. Functional reference and scoreboard execute in UVM."""
import random

def vectors(public=False):
    rng=random.Random(17 if public else 20261124)
    count=16 if public else 64
    bank=[(rng.getrandbits(30)*4 & ~4096) | (4096 if k==3 else 0) for k in range(4)]
    rows=[]
    for i in range(count):
        # Repeated partial writes exercise accumulated byte state, not just isolated pairs.
        addr=bank[i%4] if i<count//2 else (rng.getrandbits(30)*4 & ~4096)|(4096 if i%5==4 else 0)
        for wr in (1,0):
            rows.append([wr,addr,rng.getrandbits(32),i%16,
                         6 if i%3==2 else 0,6 if i%3==1 else 0,
                         ((addr>>2)&31)%5,i%9])
    return rows
