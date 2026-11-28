"""Word-aligned routing apertures, including sub-page subtraction/borrow.

Independent occupancy anchors enumerate bytes; they do not reuse DUT decode
expressions. The task still has three APB targets and one unretired transaction.
"""
import re
from pathlib import Path
FAMILY='x2p_word_aperture_router_v1'
SOURCE=Path(__file__).resolve()

def validate(c):
    if not isinstance(c,dict) or set(c)!= {'task_id','windows','purpose'}:raise ValueError('Exact contract fields required')
    if not isinstance(c['task_id'],str) or not re.fullmatch(r'x2p_router_[a-z]+_v1',c['task_id']):raise ValueError('Invalid task identity')
    if not isinstance(c['purpose'],str) or not 10<=len(c['purpose'])<=240:raise ValueError('Explain the engineering variation')
    w=c['windows']
    if not isinstance(w,list) or len(w)!=3:raise ValueError('Exactly three targets')
    for i,row in enumerate(w):
        if not isinstance(row,list) or len(row)!=2 or any(type(x)!=int for x in row):raise ValueError('Integer window required')
        base,size=row
        if base<4 or base%4 or not 4<=size<=16384 or size%4 or base+size>2**32-8:raise ValueError('Unsupported word aperture')
        if base<=0xf000<base+size:raise ValueError('Reserved unmapped reset address')
        for old,n in w[:i]:
            if max(old,base)<min(old+n,base+size):raise ValueError('Overlapping windows')
    if w[0][0]+w[0][1]>=2**31:raise ValueError('High-bit alias control requires low target zero')
    alias=w[0][0]^(1<<31)
    if any(b<=alias<b+n for b,n in w):raise ValueError('Alias witness is mapped')
    if max(n for b,n in w)<=4096:raise ValueError('Bit12 fault is inapplicable')
    if all(b%4096==0 for b,n in w):raise ValueError('This profile requires at least one sub-page base')
    if not any(b%4096 and (b//4096+1)*4096<b+n for b,n in w):raise ValueError('A non-page base must cross a global page boundary')
    if mask_fault(c) is None:raise ValueError('Mask mutation lacks a differing word-offset witness')
    return c

def mask_fault(c):
    for lane,(base,size) in enumerate(c['windows']):
        if base%4096:
            for offset in range(0,size,4):
                if ((base+offset)&(size-1))!=offset:return lane,offset
    return None

def anchors(c):
    validate(c);owners={}
    for lane,(base,size) in enumerate(c['windows']):
        for offset,address in enumerate(range(base,base+size)):
            if address in owners:raise ValueError('Duplicate owner')
            owners[address]=(lane,offset)
    points={0,0xf000,0xfffffffc,c['windows'][0][0]^(1<<31)}
    for base,size in c['windows']:
        points.update((base-4,base,base+4,base+size-4,base+size,base+size+4))
        for bit in range(2,15):
            offset=1<<bit
            if offset<size:points.update((base+offset-4,base+offset,base+offset+4))
        # Cross a GLOBAL 4-KiB boundary within the aperture. Exact subtraction,
        # not low-bit slicing, defines the peripheral address on either side.
        boundary=(base//4096+1)*4096
        if boundary<base+size:points.update((boundary-4,boundary,boundary+4))
    return [[format(a,'08x'),*owners.get(a,(-1,0))] for a in sorted(points)]

def obligations(c):
    validate(c)
    return {'schema':'word-aperture-obligations-v1','windows':c['windows'],
            'new_contract_behavior':'Global-to-local subtraction for non-page-aligned bases, including a global page carry within one target',
            'parameter_requirements':['exact_aperture_endpoints','small_aperture_aliasing','local_offset_bit12','global_page_carry_with_nonzero_base'],
            'independent_anchor_method':'enumerated byte ownership','negative_applicability':'bit12 requires a window >4096 bytes; base-mask control requires a non-page-aligned base',
            'status':'Derived; no admission without actual controls and matching runtime qualification'}

def augment(out,c,metadata):
    lane,witness_offset=mask_fault(c)
    base,size=c['windows'][lane]
    ref=(out/'fixtures/task002/reference.sv').read_text();needle="local_address=a-32'h%x;"%base
    if ref.count(needle)!=1:raise ValueError('Reference translation changed')
    fault=ref.replace(needle,"local_address=a & 32'h%x;"%(size-1))
    # Applicability is checked against actual word offsets, not the parameter name.
    if ((base+witness_offset)&(size-1))==witness_offset:raise ValueError('Invalid mask witness')
    (out/'fixtures/task002/bad_base_mask.sv').write_text(fault)
    q=metadata['quality'];q['negative_controls'].append({'source':'fixtures/task002/bad_base_mask.sv','first_case':'generated_boundaries','violation':'Uses global address masking instead of subtracting a non-page-aligned target base'})
    q['minimum_negative_controls']=15;q['required_requirements'].append('G_BASE_SUBTRACTION')
    p=out/'verifier/task002/scenarios.py';s=p.read_text();old="'G_OFFSET_CARRY']";assert s.count(old)==1;p.write_text(s.replace(old,"'G_OFFSET_CARRY','G_BASE_SUBTRACTION']"))
