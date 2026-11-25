"""Decoupled request/execution/response scenarios; separate task, unchanged Task003."""
import random
REQUIRED_BINS={'aw_full','w_full','ar_full','aw_ahead','w_ahead','both_eligible',
 'read_during_partial_write','execute_during_b_stall','execute_during_r_stall',
 'b_response_full','r_response_full','apb_wait','read_error','write_error',
 'reset_queued','reset_completed_queue','long_stream','read_snapshot_changed','simultaneous_responses','b_enqueue_dequeue','r_enqueue_dequeue'}|{'strobe_%d'%i for i in range(16)}

def suite(public=False,seed=20261125):
 rng=random.Random(seed);cases=[]
 def row(w,a,data=None,st=15,ad=0,wd=0,wait=0,stall=0,err=0,start=0):return [w,a,rng.getrandbits(32) if data is None else data,st,ad,wd,wait,stall,err,start]
 def add(name,rows,requirements,recovery=None,stage=0,early=False):
  cases.append({'name':name,'sequence':'queue_reset_sequence' if stage else 'queue_capacity_sequence','rows':rows,'recovery':recovery or [],'reset_stage':stage,'requirements':requirements,'ready_mode':'early' if early else 'reactive','align_responses':name=='simultaneous_responses','align_completion':name in ('write_push_pop','read_push_pop')})
 n=12 if public else 36
 add('write_pipeline',[row(1,0x100+(i%5)*4,st=i%16,stall=64 if i==0 else 2,wait=i%3,err=i%4==1) for i in range(n)],['D_WRITE_RESPONSES','D_THREE_CREDITS','D_WRAP','D_ERROR'],[row(0,0x100+i*4) for i in range(5)])
 add('read_pipeline',[row(0,0x200+i*4,stall=64 if i==0 else 2,wait=i%3,err=i%4==1) for i in range(n)],['D_READ_RESPONSES','D_THREE_CREDITS','D_WRAP','D_ERROR'])
 for kind in ('b','r'):
  rows=[row(int(kind=='b'),0x300+i*4,stall=80) for i in range(3)]+[row(int(kind!='b'),0x340+i*4,start=16,stall=5) for i in range(6)]
  add('opposite_during_'+kind,rows,['D_INDEPENDENT_EXECUTOR','D_CROSS_DIRECTION_PROGRESS'])
 # A delayed read response must retain data sampled before a later write.
 for wr in (0,1):
  add('write_push_pop' if wr else 'read_push_pop',[row(wr,0xa00+i*4,wait=32 if i==1 else 0) for i in range(6)],['D_RESPONSE_PUSH_POP'],early=True)
 add('read_snapshot',[row(0,0x400,stall=100),row(1,0x400,data=0x12345678,start=12),row(1,0x400,data=0x87654321,start=24),row(0,0x400,start=36,stall=4)],['D_READ_SNAPSHOT','D_MEMORY_ORDER'])
 for order in ('aw','w'):
  rows=[row(1,0x500+i*4,ad=64 if order=='w' else 0,wd=64 if order=='aw' else 0,stall=8) for i in range(3)]+[row(0,0x540+i*4,start=8) for i in range(3)]
  add('partial_'+order,rows,['D_INDEPENDENT_HALVES','D_PARTIAL_READ_PROGRESS'])
 add('round_robin',[row(i%2,0x600+(i%7)*4,wait=3,stall=12) for i in range(n*2)],['D_ROUND_ROBIN','D_ORDER','D_LONG_STREAM'])
 add('simultaneous_responses',[row(0,0x900,stall=9),row(1,0x904,stall=6)],['D_SIMULTANEOUS_RESPONSES'],early=True)
 add('early_ready',[row(i%2,[0,4,0x80000000,0xfffffffc][i%4],wait=i%3) for i in range(n*2)],['D_EARLY_READY','D_ADDRESS'],early=True)
 for k in range(1 if public else 3):
  rows=[]
  for i in range(20 if public else 72):
   w=rng.randrange(2);d=rng.choice([0,1,7,31]);order=rng.randrange(3)
   rows.append(row(w,0x10000+rng.randrange(8)*4,st=rng.randrange(16),ad=d if order==1 else 0,wd=d if order==2 and w else 0,wait=rng.choice([0,1,7,32]),stall=rng.choice([0,1,7,32,64]),err=rng.randrange(2)))
  add('random_%d'%k,rows,['D_RANDOM_INTERLEAVING','D_LONG_STREAM'])
 for stage in range(1,9):
  rows=[row(1,0x800+i*4,wait=64 if stage==5 and i==0 else 0,stall=100) for i in range(3)]+[row(0,0x840+i*4,wait=64 if stage==6 and i==0 else 0,stall=100) for i in range(3)]
  for i,r in enumerate(rows):
   if stage==1 and r[0]:r[5]=100
   if stage==2 and r[0]:r[4]=100
   if stage==3 and not r[0]:r[4]=100
   if stage==4 and r[0]:r[5]=100
   if stage in (5,7) and not r[0]:r[9]=16
   if stage in (6,8) and r[0]:r[9]=16
  recovery=[row(0,0x8c0),row(1,0x8c4)]+[row(0,0x800+i*4) for i in range(3)]+[row(1,0x880,data=0x55aa55aa),row(0,0x880)]
  add('reset_%d'%stage,rows,['D_RESET_STAGE_%d'%stage,'D_RESET_CREDITS','D_RESET_RESPONSES','D_RESET_MEMORY'],recovery,stage)
 return cases
