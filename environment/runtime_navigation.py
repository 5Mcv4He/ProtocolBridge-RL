"""Version 2 event-window projection; original v1 observations stay unchanged.
Used by generated queue capsules. Only already-captured public laboratory pins.
"""
import re
from environment.runtime_tools import observation as legacy_observation
EVENTS=('AW','W','AR','APB_SETUP','APB_COMPLETE','B','R')
def valid_start(value):
 return (type(value)==int and 0<=value<4096) or (isinstance(value,str) and re.fullmatch(r'(AW|W|AR|APB_SETUP|APB_COMPLETE|B|R):([0-9]{1,4})',value) is not None)
def observation(record,detail,start=None,count=12):
 if type(count)!=int or not 1<=count<=12 or (start is not None and not valid_start(start)):raise ValueError('Invalid event window')
 if not detail:return legacy_observation(record,False)
 trace=record.get('timeline')
 if not trace:return legacy_observation(record,True)
 events=[s for s in trace['samples'] if s['phase']=='pre' and any(e in EVENTS for e in s['events'])]
 selected=None;kind='cycle';requested=start
 if isinstance(start,str):
  event,index=start.split(':');matches=[s for s in events if event in s['events']]
  if int(index)>=len(matches):
   out=legacy_observation(record,True,0,1);out['rows']=[]
   out['window']={'status':'NOT_CAPTURED','selector':start,'matches':len(matches)}
   return out
  selected=matches[int(index)];kind='event'
 elif start is None:
  end=trace.get('first_error')
  if end:selected=end;kind='first_error'
  elif events:selected=events[0];kind='first_activity'
  else:start=0;kind='no_activity'
 if selected:start=max(0,selected['cycle']-2)
 out=legacy_observation(record,True,start,count)
 out['window']={'status':'FOUND','selector':requested,'start':start,'count':count,'anchor_cycle':selected['cycle'] if selected else None,'anchor_kind':kind}
 out['event_counts']={e:sum(e in s['events'] for s in events) for e in EVENTS}
 return out
