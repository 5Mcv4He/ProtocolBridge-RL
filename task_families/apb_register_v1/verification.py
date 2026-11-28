"""Finite stimulus and independently enumerated state-transition anchors.

These are trusted producer inputs, never model-visible private evaluation data.
The pin-level checker remains responsible for actual activity and timing.
"""
import random
from .contract import validate


def update_bytes(old,data,strobe,mask,access):
    if access=='ro':return old
    result=[]
    for lane,(before,value,writable) in enumerate(zip(old.to_bytes(4,'little'),data.to_bytes(4,'little'),mask.to_bytes(4,'little'))):
        enabled=writable if strobe&(1<<lane) else 0
        after=(before & ~(value & enabled)) if access=='w1c' else ((before & ~enabled)|(value & enabled))
        result.append(after)
    return int.from_bytes(bytes(result),'little')


def scenarios(c,seed=0,random_count=24):
    validate(c)
    if type(seed)!=int or not 0<=seed<2**32 or type(random_count)!=int or not 0<=random_count<=256:raise ValueError('Bounded stimulus inputs required')
    regs=c['registers'];addresses={r['address'] for r in regs};rows=[]
    def readall():rows.extend([0,r['address'],0,0] for r in regs)
    def reset():rows.append([2,0,0,0]);readall()
    readall()
    # Reset for each strobe preserves a W1C witness instead of repeatedly
    # clearing an already-zero state. Peer reads check register identity.
    for strobe in range(16):
        reset()
        for r in regs:
            rows.append([1,r['address'],0xffffffff,strobe]);readall()
            rows.append([1,r['address'],0,strobe]);readall()
    reset()
    misses=sorted({r['address']+1 for r in regs}|{a for r in regs for a in (r['address']-4,r['address']+4) if 0<=a<=0xffffffff and a not in addresses})
    for address in misses:
        rows.extend([[1,address,0x55aa9966,15],[0,address,0,0]]);readall()
    rng=random.Random(seed)
    for i in range(random_count):
        r=regs[rng.randrange(len(regs))]
        rows.append([1,r['address'],rng.getrandbits(32),rng.randrange(16)]);readall()
    reset()
    return rows


def config_sv(c):
    validate(c);regs=c['registers'];n=len(regs)
    s='localparam integer REG_COUNT=%d;\nlocalparam integer ACCESS_WAITS=%d;\n'%(n,c['wait_cycles'])
    for field,name in [('address','reg_address'),('reset','reset_word'),('write_mask','write_mask')]:
        s+='function automatic logic[31:0] %s(input integer i);\n case(i)\n'%name
        for i,r in enumerate(regs):s+=" %d:return 32'h%08x;\n"%(i,r[field])
        s+=" default:return 32'hx;\n endcase\nendfunction\n"
    s+='function automatic integer mode(input integer i);\n case(i)\n'
    for i,r in enumerate(regs):s+=' %d:return %d;\n'%(i,{'rw':0,'ro':1,'w1c':2}[r['access']])
    s+=' default:return -1;\n endcase\nendfunction\n'
    return s


def anchors_sv(c):
    validate(c);s='initial begin\n'
    # Known byte-oriented transformations independently check the SV state
    # predictor at elaborated contract values. They do not replace transactions.
    for i,r in enumerate(c['registers']):
        for data,strobe in ((0xffffffff,0),(0xffffffff,5),(0xa1b2c3d4,10),(0,15)):
            expected=update_bytes(r['reset'],data,strobe,r['write_mask'],r['access'])
            s+=" if(next_word(%d,32'h%08x,32'h%08x,4'h%x)!==32'h%08x) $fatal(1,\"PB_INFRA: independent state anchor mismatch\");\n"%(i,r['reset'],data,strobe,expected)
    return s+' $display("PB_ORACLE_ANCHORS_OK");\nend\n'
