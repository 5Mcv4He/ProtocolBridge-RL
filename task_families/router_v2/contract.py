"""Finite address-routing production domain; capacity/timing remain unchanged.

An enumerated byte ownership map is deliberately separate from interval decoder
expressions in RTL and UVM. It reduces shared-expression risk, not shared-Spec risk.
"""
from task_families.router_v1.generate import validate

def validate_domain(c):
    validate(c)
    if max(n for _,n in c['windows'])<8192:raise ValueError('Existing bit12 negative is inapplicable to all-4KiB windows')
    # The inherited alias mutation ignores bit31 of lane zero. Its witness must
    # not be a legitimate request to another lane.
    alias=c['windows'][0][0]^(1<<31)
    if any(b<=alias<b+n for b,n in c['windows']):raise ValueError('Inherited high-bit alias negative lacks an unmapped witness')
    return c

def anchors(c):
    validate_domain(c);owners={}
    for lane,(base,size) in enumerate(c['windows']):
        for offset,address in enumerate(range(base,base+size)):
            if address in owners:raise ValueError('Multiple byte owners')
            owners[address]=(lane,offset)
    points={0,0xf000,0xfffffffc,c['windows'][0][0]^(1<<31)}
    for base,size in c['windows']:
        points.update((base-4,base,base+4,base+size-4,base+size,base+size+4))
        for offset in (1<<b for b in range(2,16) if 1<<b<size):points.update((base+offset-4,base+offset,base+offset+4))
    return [[format(a,'08x'),*owners.get(a,(-1,0))] for a in sorted(points)]

def obligations(c):
    validate_domain(c);w=c['windows']
    return {'schema':'router-contract-obligations-v2','protocol':'Inherited AXI4-Lite slave / APB4 three-target master; one global unretired transaction',
      'parameter_requirements':['full_address_identity','exact_local_offset','inside_offset_carries'],
      'interaction_requirements':['target_change_with_wait_and_response_backpressure','unmapped_request_has_no_apb_and_one_decerr','reset_cancels_selected_target'],
      'adjacent_pairs':[[i,j] for i,(b,n) in enumerate(w) for j,(a,m) in enumerate(w) if i!=j and b+n==a],
      'non_power_two_targets':[i for i,(_,n) in enumerate(w) if n&(n-1)],
      'semantic_identity':{'windows':w,'role':'single-outstanding-local-address-router'},
      'status':'Derived obligations; actual execution and interaction coverage require industrial evidence, not just generated rows.'}
