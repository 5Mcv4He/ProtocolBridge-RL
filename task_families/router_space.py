"""Capability-bounded task-space routing, not a protocol Cartesian product.

This classifier separates contradictory requests, missing engineering contracts,
unsupported resource scopes, and candidates that current producers can build.
It never returns an admission decision.
"""
from task_families.router_v2.contract import validate_domain as page_contract
from task_families.router_v4.contract import validate as word_contract


def classify(request):
    fields={'contract','upstream','downstream','targets','unretired_capacity','delivery'}
    if not isinstance(request,dict) or set(request)!=fields:
        return {'status':'invalid_description','can_generate':False,'reason':'Exact engineering relationship fields required'}
    up,down=request['upstream'],request['downstream']
    keys={'protocol','role','data_bits','address_bits','max_beats'}
    if any(not isinstance(x,dict) or set(x)!=keys for x in (up,down)):
        return {'status':'invalid_description','can_generate':False,'reason':'Typed protocol endpoints required'}
    if any(type(x[k])!=int or x[k]<1 for x in (up,down) for k in ('data_bits','address_bits','max_beats')):
        return {'status':'invalid_description','can_generate':False,'reason':'Positive integer interface bounds required'}
    if any(x['protocol'] in ('AXI4-Lite','APB4') and x['max_beats']!=1 for x in (up,down)):
        return {'status':'contradictory_protocol_contract','can_generate':False,'reason':'These endpoint protocols have no native burst transaction'}
    if up['protocol']!='AXI4-Lite' or down['protocol']!='APB4':
        return {'status':'requires_contract_and_verification_resource','can_generate':False,'reason':'No qualified conversion/splitting semantics for the requested endpoints in this producer'}
    if up['role']!='slave' or down['role']!='master':
        return {'status':'unqualified_endpoint_roles','can_generate':False,'reason':'Existing task resources exercise DUT AXI slave and APB master roles only'}
    if any(x['data_bits']!=32 or x['address_bits']!=32 for x in (up,down)):
        return {'status':'requires_width_oracle','can_generate':False,'reason':'Width adaptation needs independent byte-lane and split/merge rules'}
    if type(request['targets'])!=int or type(request['unretired_capacity'])!=int or request['targets']<1 or request['unretired_capacity']<1:
        return {'status':'invalid_description','can_generate':False,'reason':'Positive target/capacity counts required'}
    if request['targets']!=3 or request['unretired_capacity']!=1:
        return {'status':'requires_composition_verification','can_generate':False,'reason':'Changing topology or concurrency requires more than the routing obligations'}
    if request['delivery']!='rtl_implementation':
        return {'status':'requires_artifact_and_reward_profile','can_generate':False,'reason':'A checker, stimulus or repair artifact needs its own delivery and qualification contract'}
    for profile,validator in [('page_windows_v2',page_contract),('word_apertures_v1',word_contract)]:
        try:validator(request['contract'])
        except (ValueError,TypeError,KeyError,IndexError,AttributeError):continue
        return {'status':'candidate_generation_supported','can_generate':True,'profile':profile,'admitted':False,
                'resources':['axi4lite_active_master_32','apb4_active_slave_32','router_transaction_model','router_timing_checks'],
                'requirement':'Source-bound instance controls, current runtime qualification and independent quality challenge still required'}
    return {'status':'outside_qualified_generation_domain','can_generate':False,'reason':'Reject before EDA; review overlap, alignment, bounds and fault applicability. This is not a claim that every rejected circuit is physically impossible.'}
