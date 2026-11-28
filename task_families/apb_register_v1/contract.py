"""A bounded register domain, distinct from the VIP's generic memory predictor."""
import re

FAMILY='apb-register-contract-v1'

def validate(c):
    if not isinstance(c,dict) or set(c)!={'task_id','wait_cycles','registers'}:
        raise ValueError('Exact register-contract fields required')
    if not isinstance(c['task_id'],str) or not re.fullmatch(r'apb_register_[a-z][a-z0-9_]{0,40}_v1',c['task_id']):
        raise ValueError('Invalid task identity')
    if type(c['wait_cycles'])!=int or not 0<=c['wait_cycles']<=3:raise ValueError('Zero to three Access wait edges supported')
    regs=c['registers']
    if not isinstance(regs,list) or not 2<=len(regs)<=4:raise ValueError('Two to four independently addressed registers required')
    seen=set()
    for r in regs:
        if not isinstance(r,dict) or set(r)!={'address','reset','write_mask','access'}:raise ValueError('Exact register fields required')
        if any(type(r[k])!=int or not 0<=r[k]<=0xffffffff for k in ('address','reset','write_mask')):raise ValueError('32-bit unsigned register fields required')
        if r['address']%4 or r['address']>0xffffffec or r['address'] in seen:raise ValueError('Distinct aligned addresses with room for miss witnesses required')
        seen.add(r['address'])
        if r['access'] not in ('rw','ro','w1c'):raise ValueError('Unsupported register semantics')
        if (r['access']=='ro')!=(r['write_mask']==0):raise ValueError('Only read-only registers have an empty write mask')
        if r['access']=='w1c' and not (r['reset']&r['write_mask']):raise ValueError('W1C clear witness requires set writable reset bits')
    if not any(r['access']=='rw' and r['write_mask']&0xff and r['write_mask']&0xff000000 for r in regs):
        raise ValueError('A byte-preservation witness across distant byte lanes is required')
    if len({r['reset'] for r in regs})!=len(regs):raise ValueError('Distinct reset words required for independent identity anchors')
    return c

def obligations(c):
    validate(c)
    rows=[dict(id='APB_PHASE',kind='protocol',witness='Setup precedes Access; request stable through waits'),
          dict(id='ADDRESS_IDENTITY',kind='parameter',witness='Read every distinct reset word; interleave writes and read all targets'),
          dict(id='STROBE_STATE',kind='interaction',witness='All16 PSTRB values × each writable register, readback and unaffected-peer checks'),
          dict(id='UNMAPPED',kind='functional',witness='Aligned holes and unaligned addresses: PSLVERR, zero read, no state change'),
          dict(id='IDLE_RESET',kind='lifecycle',witness='Reset between completed requests restores all words'),
          dict(id='WAIT_ACCOUNTING',kind='timing',witness='Exactly configured Access edges with PREADY low for every completion')]
    if any(r['access']=='w1c' for r in c['registers']):rows.append(dict(id='W1C_STROBE',kind='interaction',witness='On reset-set bits: write-one clears enabled lanes, write-zero and disabled lanes preserve'))
    if any(r['access']=='ro' for r in c['registers']):rows.append(dict(id='RO_WRITE',kind='functional',witness='Writes complete OK without changing read-only value'))
    if any(r['access']=='rw' and r['write_mask']!=0xffffffff for r in c['registers']):rows.append(dict(id='RESERVED_BITS',kind='interaction',witness='Byte strobe and bit write mask both restrict updates; other reset bits preserved'))
    return rows
