"""Observe a VCS/UVM simulation's actual banners, rather than trust inventory labels."""
import re

def observed(simulation_log):
    vcs=re.findall(r'Compiler version (\S+); Runtime version (\S+);',simulation_log)
    uvm=re.findall(r'^\s*(UVM-1\.[^\s]+)\s*$',simulation_log,re.M)
    if len(set(vcs))!=1 or len(set(uvm))!=1:
        raise ValueError('Missing or ambiguous runtime identity')
    return {'vcs_compiler':vcs[0][0],'vcs_runtime':vcs[0][1],'uvm':uvm[0][4:]}

def check(identity,declared):
    if identity['vcs_compiler']!=identity['vcs_runtime']:
        raise ValueError('Compiler/runtime versions differ')
    if re.sub(r'_Full64$', '', identity['vcs_runtime'])!=declared['vcs']:
        raise ValueError('Declared VCS differs from actual runtime')
    if identity['uvm']!=declared['uvm']:
        raise ValueError('Declared UVM differs from actual runtime')
    return True
