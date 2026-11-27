"""Versioned combined profile; installed only into admitted queue capsules.

Old profiles remain unchanged. Every development observation carries the exact
candidate identity and whether that result still describes the current file.
"""
import hashlib
import json
from environment.engineering_session import Session as EngineeringSession
from environment.runtime_session import Session as RuntimeSession
from environment.synthesis_session import SynthesisMixin

VERSION = 'engineering-lab-v1'
PROFILE = {
    'id': VERSION, 'tools': ['compile', 'inspect', 'synth_check', 'experiment', 'observe'],
    'max_agent_actions': 20, 'max_public_test_calls': 2, 'max_compile_calls': 2,
    'max_inspect_calls': 2, 'max_synth_calls': 2, 'max_experiment_calls': 3,
    'max_observe_calls': 4, 'max_observation_chars': 16500,
    'candidate_binding': 'sha256-current-and-result-v1',
    'scope': 'retirement-queue capsules with runtime-events-v2; independent terminal reward',
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extend_prompt(prompt):
    from environment.runtime_session import extend_prompt as runtime_prompt
    from environment.engineering_session import extend_prompt as engineering_prompt
    from environment.synthesis_session import extend_prompt as synthesis_prompt
    text = runtime_prompt(prompt, 'runtime-events-v2')
    text = text.replace(' First read the files and test the starting candidate before repairing it.', '')
    return synthesis_prompt(engineering_prompt(text)) + (
        ' Combined profile engineering-lab-v1: all tools share 20 total actions, '
        'not separate episode budgets. A candidate_binding gives current_sha256, '
        'result_sha256 and is_current. A prior PASS does not apply after an edit. '
        'inspect and observe query recorded results without rerunning the current RTL. '
        'Use compile for syntax, synth_check for synthesis feasibility, test for full '
        'public regression, experiment for a specific engineering hypothesis, and '
        'observe for relevant event windows. None replaces terminal verification.')


class Session(SynthesisMixin, EngineeringSession, RuntimeSession):
    def __init__(self, *args, **kwargs):
        # Fail closed outside the explicitly upgraded capsule.
        from environment.runtime_session import PROFILES
        if 'runtime-events-v2' not in PROFILES:
            raise ValueError('engineering-lab-v1 requires an event-v2 queue capsule')
        kwargs['capability'] = 'runtime-events-v2'
        super().__init__(*args, **kwargs)
        self._save_profile()

    def _save_profile(self):
        (self.out / 'capabilities.json').write_text(json.dumps(PROFILE, indent=2) + '\n')

    def handle(self, action):
        previous = len(self.trace)
        before = digest(self.work / 'bridge.sv')
        obs = super().handle(action)
        if len(self.trace) == previous:
            return obs
        event = self.trace[-1]
        tool = action.get('tool') if isinstance(action, dict) else None
        if event['executed'] and tool in ('edit', 'submit', 'test', *PROFILE['tools']):
            current = digest(self.work / 'bridge.sv')
            result = current if tool in ('edit', 'submit') else before
            if tool == 'inspect':
                result = self.public[-1]['source_sha256']
            elif tool == 'observe':
                result = self.lab[-1]['result']['source_sha256']
            obs['candidate_binding'] = {'current_sha256': current,
                                        'result_sha256': result,
                                        'is_current': current == result}
            if len(json.dumps(obs)) > PROFILE['max_observation_chars']:
                raise RuntimeError('Combined observation bound')
            (self.out / 'trace.json').write_text(json.dumps(self.trace, indent=2) + '\n')
        return obs
