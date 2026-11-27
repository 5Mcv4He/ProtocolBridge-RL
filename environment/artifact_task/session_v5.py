"""Versioned action-format diagnostics; never normalize or execute rejected input."""
import json
from .session_v4 import Session as PreviousSession,sha,save,prompt
VERSION='engineering-artifact-session-v5'
EXAMPLES={
 'read':'{"tool":"read","file":"spec.md"}',
 'edit':'{"tool":"edit","content":"complete file contents"}',
 'test':'{"tool":"test"}',
 'submit':'{"tool":"submit"}',
}
class Session(PreviousSession):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        p=self.out/'session.json';record=json.loads(p.read_text());record['version']=VERSION;save(p,record)
    def handle(self,action):
        observation=super().handle(action)
        if observation.get('reason')=='invalid_action_format':
            tool=action.get('tool') if isinstance(action,dict) else None
            example=EXAMPLES.get(tool) if isinstance(tool,str) else None
            observation['instruction']=(
                'REJECTED: zero actions executed and no file changed. '+
                ('For '+tool+', use exactly this shape: '+example+'. No additional keys. '+
                 ('The edit action has NO file key; its target is already fixed. ' if tool=='edit' else '')
                 if example else
                 'Send ONE object only. To edit, send {"tool":"edit","content":"complete file contents"}. ')+
                'End the reply immediately after that object. Do not append a test action; request test in a later turn after receiving EDITED.')
            # PreviousSession owns execution, budgets and the same observation object.
            # Only this explicitly versioned, constant diagnostic is replaced.
            save(self.out/'trace.json',self.trace)
        return observation
