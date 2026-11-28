"""Evaluate the candidate error signal, not candidate assertions or logs."""
import argparse,json,re
from pathlib import Path
from verifier.event_runtime import run
from verifier.independent_formal.campaign import sha,ROOT,source_policy as restricted_rtl
from verifier.fifo_checker.campaign_v3 import interpret
from .model import corpus
TASKS={'register_checker_rw_v1':'rw','register_checker_w1c_v1':'w1c'}

def source_policy(text):
    reason=restricted_rtl(re.sub(r'\bmodule\s+register_checker\b','module accumulator',text,count=1))
    if reason:return reason
    clean=re.sub(r'/\*.*?\*/|//[^\n]*',' ',text,flags=re.S)
    if '#' in clean:return 'delay_or_parameter_not_supported'
    header=re.search(r'\bmodule\s+register_checker\s*\((.*?)\)\s*;',clean,re.S)
    if not header:return 'fixed_ansi_interface_required'
    expected=[('clk','input',1),('rst_n','input',1),('event_valid','input',1),('is_write','input',1),('address','input',4),('write_data','input',8),('read_data','input',8),('error','output',1)]
    actual=[];direction=None;width=1
    for port in header[1].split(','):
        d=re.search(r'\b(input|output|inout)\b',port)
        if d:direction=d[1];width=1
        b=re.search(r'\[\s*(\d+)\s*:\s*(\d+)\s*\]',port)
        if b:width=abs(int(b[1])-int(b[2]))+1
        elif '[' in port:return 'literal_interface_width_required'
        words=re.findall(r'[A-Za-z_][A-Za-z_0-9]*',re.sub(r'\[[^\]]*\]','',port));actual.append((words[-1] if words else None,direction,width))
    return None if actual==expected else 'fixed_interface'

def bench():return '''`timescale 1ns/1ps
module tb;
 bit clk=0;always #5 clk=~clk;
 bit rst_n,event_valid,is_write;bit [3:0] address;bit [7:0] write_data,read_data;wire error;
 integer f,n,r,a,b,c,d,e,g,expected;integer cases=0;
 register_checker dut(.clk(clk),.rst_n(rst_n),.event_valid(event_valid),.is_write(is_write),.address(address),.write_data(write_data),.read_data(read_data),.error(error));
 initial begin
  f=$fopen("events.txt","r");if(!f)begin $display("PB_CHECKER_INFRA missing_vectors");$finish;end
  r=$fscanf(f,"%d\\n",n);if(r!=1 || n<1)begin $display("PB_CHECKER_INFRA invalid_count");$finish;end
  for(integer i=0;i<n;i=i+1)begin
   @(negedge clk);r=$fscanf(f,"%d %d %d %d %d %d %d\\n",a,b,c,d,e,g,expected);
   if(r!=7)begin $display("PB_CHECKER_INFRA incomplete_vectors");$finish;end
   rst_n=a;event_valid=b;is_write=c;address=d;write_data=e;read_data=g;
   @(posedge clk);#1;
   if(error!==expected[0])begin $display("PB_CHECKER_MISMATCH row=%0d expected=%0d observed=%0b",i,expected,error);$finish;end
   cases++;
  end
  $display("PB_CHECKER_COMPLETE rows=%0d",cases);$finish;
 end
 initial begin #1000000;$display("PB_CHECKER_INFRA watchdog");$finish;end
endmodule
'''
def grade(task,source,out,phase='public'):
    if task not in TASKS:raise ValueError('Unknown register checker')
    rows,coverage=corpus(TASKS[task],phase)
    result=run(source,out,task=task,bench=bench(),rows=rows,source_policy=source_policy,interpret=interpret,identity={'phase':phase,'grader_sha256':sha(__file__),'model_sha256':sha(Path(__file__).with_name('model.py')),'runtime_sha256':sha(ROOT/'verifier/event_runtime.py'),'planned_event_obligations':coverage})
    if result['reward']==1:result['executed_event_obligations']=coverage
    (Path(out)/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('task',choices=TASKS);p.add_argument('source');p.add_argument('out');p.add_argument('--phase',default='public',choices=['public','terminal','evaluation']);a=p.parse_args();print(json.dumps(grade(a.task,a.source,a.out,a.phase),indent=2))
