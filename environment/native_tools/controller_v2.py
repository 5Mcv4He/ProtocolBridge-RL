"""Strict raw native arguments, pre-request budgets and explicit receipt evidence."""
import hashlib,json
from .controller import Controller as PreviousController,prompt as previous_prompt
from environment.artifact_task.session_v4 import save
VERSION='engineering-native-tools-v2'

def prompt(filename,actions=20,tests=4):
    return previous_prompt(filename,actions,tests)+' Native calls in a single response execute in order, each consumes an action. They cannot depend on feedback from another call in that same response. At most '+str(actions)+' model requests are allowed.'

def strict_object(raw):
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise ValueError('duplicate key')
            result[key]=value
        return result
    if not isinstance(raw,str):raise ValueError('native arguments must be raw JSON text')
    value=json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
    if not isinstance(value,dict):raise ValueError('object required')
    return value

def digest(observation):
    return hashlib.sha256(json.dumps(observation,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

class Controller(PreviousController):
    def __init__(self,session,max_requests=None):
        super().__init__(session)
        self.max_requests=max_requests if max_requests is not None else session.max_actions
        if type(self.max_requests)!=int or not 1<=self.max_requests<=20:raise ValueError('Invalid request limit')
        self.requests=[]
        save(session.out/'native-interface.json',{'version':VERSION,'max_model_requests':self.max_requests})
    def dispatch(self,packet):
        if isinstance(packet,dict) and packet.get('kind')=='model_request':return self.request(packet)
        # Keep the raw proposal, including malformed/empty/duplicate JSON.
        raw=packet.get('arguments') if isinstance(packet,dict) else None
        try:args=strict_object(raw)
        except (ValueError,TypeError):args=None
        parsed=dict(packet,arguments=args) if isinstance(packet,dict) else packet
        reply=super().dispatch(parsed)
        self.calls[-1]['raw_arguments']=raw
        text=json.dumps(reply['observation'],ensure_ascii=False,separators=(',',':'))
        if packet['name'] not in ('read','edit','test','submit'):text='Error: '+text
        self.calls[-1]['observation_text_sha256']=hashlib.sha256(text.encode()).hexdigest()
        save(self.session.out/'native-calls.json',self.calls)
        return reply
    def request(self,packet):
        fields={'kind','call_id','request_index','prior_tool_results'}
        if set(packet)!=fields or type(packet['request_index'])!=int or packet['request_index']!=len(self.requests)+1 or packet['call_id']!='request-'+str(packet['request_index']):
            raise ValueError('Invalid request envelope')
        if not isinstance(packet['prior_tool_results'],list):raise ValueError('Invalid feedback projection')
        prior=[];seen=set()
        for row in packet['prior_tool_results']:
            if not isinstance(row,dict) or set(row)!={'call_id','text_sha256'}:raise ValueError('Invalid feedback record')
            call=next((c for c in self.calls if c['request']['call_id']==row['call_id']),None)
            if call is None or row['call_id'] in seen or row['text_sha256']!=call['observation_text_sha256'] or not call['transport_returned']:
                raise ValueError('Unbound runtime feedback')
            seen.add(row['call_id']);prior.append(row['call_id'])
        allowed=not self.session.done and packet['request_index']<=self.max_requests
        self.requests.append({'index':packet['request_index'],'allowed':allowed,'prior_tool_results':prior,'response_received':False})
        save(self.session.out/'native-requests.json',self.requests)
        return {'call_id':packet['call_id'],'observation':{'status':'REQUEST_ALLOWED' if allowed else 'REQUEST_DENIED'},'stop':not allowed}
    def response_received(self,event):
        if event.get('type')!='assistant/message':return
        data=event.get('data',{});index=data.get('step')
        if data.get('turn')!=1 or type(index)!=int or not 1<=index<=len(self.requests):raise ValueError('Unmatched model response')
        row=self.requests[index-1]
        if not row['allowed'] or row['response_received']:raise ValueError('Duplicate or denied response')
        row['response_received']=True;row['response_event_seq']=event['seq'];row['usage']=data.get('usage')
        for call in self.calls:
            if call['request']['call_id'] in row['prior_tool_results']:
                call['model_receipt_confirmed']=True
                if call['action_index'] is not None:self.session.trace[call['action_index']-1]['observation_delivered']=True
        save(self.session.out/'native-requests.json',self.requests)
        save(self.session.out/'native-calls.json',self.calls)
        save(self.session.out/'trace.json',self.session.trace)
