"""Finite public-test budget conditions; all other Policy v1 fields stay fixed."""
import copy
VERSION='verification-budget-v1'
CONDITIONS={2:'test2',6:'test6'}

def validate(policy,legacy):
    if policy.get('version')==1:return legacy(policy)
    if type(policy.get('version')) is not int or policy['version']!=2:
        raise ValueError('Unsupported budget policy version')
    budget=policy.get('max_public_test_calls')
    if type(budget) is not int or budget not in CONDITIONS or policy.get('policy_id')!='test_diagnostic':
        raise ValueError('Unsupported verification budget condition')
    old=copy.deepcopy(policy);old.update(version=1,max_public_test_calls=2)
    legacy(old)
    return policy

def derive(policy,budget,legacy):
    if budget is None:return policy
    if type(budget) is not int or budget not in CONDITIONS:raise ValueError('Unknown test budget')
    result=copy.deepcopy(policy);result.update(version=2,max_public_test_calls=budget)
    return validate(result,legacy)
