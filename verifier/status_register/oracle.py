"""Per-bit truth-table anchor, independent of generated bitwise RTL expressions."""
import random
# (old, hardware, effective clear) -> next, enumerated from the two contracts.
TABLES={
 'set_dominant':{(0,0,0):0,(0,0,1):0,(0,1,0):1,(0,1,1):1,
                 (1,0,0):1,(1,0,1):0,(1,1,0):1,(1,1,1):1},
 'clear_dominant':{(0,0,0):0,(0,0,1):0,(0,1,0):1,(0,1,1):0,
                   (1,0,0):1,(1,0,1):0,(1,1,0):1,(1,1,1):0}}
def next_value(mode,old,rst_n,write,hardware,data):
 if not rst_n:return 0
 return sum(TABLES[mode][(int(bool(old&(1<<b))),int(bool(hardware&(1<<b))),int(bool(write and data&(1<<b))))]<<b for b in range(8))
def corpus(mode,phase):
 seeds={'public':321,'terminal':663,'evaluation':997}
 if phase not in seeds:raise ValueError('Unknown phase')
 rng=random.Random(seeds[phase]);rows=[];state=0
 def add(r,w,h,d):
  nonlocal state
  state=next_value(mode,state,r,w,h,d);rows.append([r,w,h,d,state])
 # Every old state, each bit's hardware/clear/write truth-table, arbitrary other bits.
 for old in range(256):
  for bit in range(8):
   for write in (0,1):
    for hardware in (0,1):
     for clear in (0,1):
      add(0,1,255,255);add(1,0,old,255)
      h=(rng.randrange(256)&~(1<<bit))|(hardware<<bit)
      d=(rng.randrange(256)&~(1<<bit))|(clear<<bit)
      add(1,write,h,d);add(1,0,0,255)
 for i in range(512):add(int(i%17!=0),rng.randrange(2),rng.randrange(256),rng.randrange(256))
 return rows
