"""Current response-ownership capsules only; legacy grading implementation retained.

This explicitly changes the supported verifier domain. It does not inherit
historical task admission. Each instance requires its own updated controls.
"""
import json
from pathlib import Path
from environment.package_backend import Backend as Previous, sha
from task_families.router_v2.generate import verify

class Backend(Previous):
    def check(self):
        if sha(self.package/'family-manifest.json')!=self.manifest_sha256:raise ValueError('Package identity changed')
        m=verify(self.package)
        if m.get('family')!='x2p_three_target_router_v5' or m.get('execution_adapter')!='router-deployment-v1' or m.get('qualification_revision')!=2 or m.get('verifier_revision')!='response-ownership-v1':raise ValueError('Unsupported execution package')
        if sha(self.config)!=self.config_sha256:raise ValueError('Execution configuration changed')
        cfg=json.loads(self.config.read_text())
        if 'variant' in cfg or cfg.get('compile_cache'):raise ValueError('Standalone grading cannot select a control-bank variant or external cache')
        if any(sha(p)!=self.input_sha256[k] for k,p in self.inputs.items()):raise ValueError('Frozen inputs changed')

