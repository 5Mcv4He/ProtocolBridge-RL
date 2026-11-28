"""Native argument gate around the unchanged artifact-session-v4 semantics.

Neither native batches nor JSON Schema grant authority. Every dispatched call
passes this gate. Final grading is a separate operation after process shutdown.
"""
import json
from environment.artifact_task.session_v4 import Session, save

VERSION = 'engineering-native-tools-v1'


def prompt(filename, actions=20, tests=4):
    return (
        'Solve the engineering task specified by spec.md using the provided tools. '
        'Read spec.md and '+filename+' before editing or submitting. '
        'Only '+filename+' can be edited. Test runs the trusted public checker '
        'against the current file. You have at most %d total tool actions and '
        '%d public tests. Rejected actions also consume an action. ' % (actions, tests)
        + 'Submission is allowed without passing tests and ends solving. Independent '
        'terminal and held-out results are not returned. No shell, other files, '
        'reference, checker or private inputs are available. '
        'Use the registered tools; do not write tool requests as prose.'
    )


class Controller:
    def __init__(self, session):
        if not isinstance(session, Session):
            raise TypeError('Expected artifact-session-v4')
        self.session = session
        self.calls = []
        self.ids = set()
        save(session.out/'native-interface.json', {'version': VERSION})

    def dispatch(self, packet):
        # Malformed transport is an infrastructure problem, not an RTL failure.
        if (not isinstance(packet, dict) or set(packet) != {'kind','call_id','name','arguments'}
                or packet['kind'] != 'tool_request'
                or not isinstance(packet['call_id'], str)
                or not 0 < len(packet['call_id']) <= 256
                or packet['call_id'] in self.ids):
            raise ValueError('Invalid or replayed native envelope')
        self.ids.add(packet['call_id'])
        name, args = packet['name'], packet['arguments']
        shapes = {'read': {'file'}, 'edit': {'content'}, 'test': set(), 'submit': set()}
        valid = (isinstance(name,str) and name in shapes and isinstance(args,dict)
                 and set(args)==shapes[name])
        if valid and name in ('read','edit'):
            valid = isinstance(args['file' if name=='read' else 'content'], str)
        before = len(self.session.trace)
        # Never strip unexpected fields, split actions, coerce types or repair text.
        observation = self.session.handle(dict(tool=name, **args) if valid else {})
        if observation.get('reason') == 'invalid_action_format':
            observation['instruction'] = 'Call one registered tool with exactly its declared arguments. This call executed no operation.'
            save(self.session.out/'trace.json', self.session.trace)
        index = self.session.actions if len(self.session.trace)>before else None
        self.calls.append({'request':packet, 'action_index':index,
                           'executed':self.session.trace[-1]['executed'] if index else False,
                           'observation':observation,
                           'transport_returned':False, 'model_receipt_confirmed':False})
        save(self.session.out/'native-calls.json', self.calls)
        return {'call_id':packet['call_id'], 'observation':observation, 'stop':self.session.done}

    def returned(self, call_id):
        """Transport write is distinct from a subsequent model request receipt."""
        row = next(x for x in self.calls if x['request']['call_id']==call_id)
        row['transport_returned'] = True
        save(self.session.out/'native-calls.json', self.calls)
