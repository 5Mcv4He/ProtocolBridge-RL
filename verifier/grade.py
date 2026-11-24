"""Canonical grading API. Functional verification is the v3 UVM campaign.
Historical v2 results are preserved under experiments, not used for new grades.
"""
from .campaign import grade, sha as digest

if __name__=='__main__':
    import runpy
    runpy.run_module('verifier.campaign',run_name='__main__')
