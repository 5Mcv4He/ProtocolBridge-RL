"""Explicit fixed-file edit contract; no repair of old protocol proposals.

V3 requires both file and content. A matching file is consumed as an authority
check before projecting the content into the unchanged single-artifact session.
Missing, extra and mismatched fields are rejected, never silently stripped.
"""
import json
from .controller_v2 import Controller as PreviousController,strict_object,prompt
from environment.artifact_task.session_v4 import save
VERSION='engineering-native-tools-v3'
class Controller(PreviousController):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        save(self.session.out/'native-interface.json',{'version':VERSION,'max_model_requests':self.max_requests,'edit_fields':['file','content'],'fixed_file':self.session.filename})
    def dispatch(self,packet):
        if not isinstance(packet,dict) or packet.get('kind')!='tool_request' or packet.get('name')!='edit':return super().dispatch(packet)
        raw=packet.get('arguments');args=None
        try:args=strict_object(raw)
        except (ValueError,TypeError):pass
        valid=(isinstance(args,dict) and set(args)=={'file','content'} and args['file']==self.session.filename and isinstance(args['content'],str))
        projected=json.dumps({'content':args['content']},ensure_ascii=False) if valid else 'null'
        result=super().dispatch(dict(packet,arguments=projected))
        row=self.calls[-1];row['raw_arguments']=raw
        row['request']['arguments']=args
        row['argument_projection']={'fixed_file_checked':self.session.filename,'fields_consumed':['file'],'fields_forwarded':['content']} if valid else None
        save(self.session.out/'native-calls.json',self.calls)
        return result
