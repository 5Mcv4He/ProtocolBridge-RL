"""Canonical grading API. Functional verification is the v3 UVM campaign.
Task 001 X2P uses this single standard baseline; the former backend is retired.
"""
from .campaign import grade, sha as digest

if __name__=='__main__':
    import runpy
    runpy.run_module('verifier.campaign',run_name='__main__')
