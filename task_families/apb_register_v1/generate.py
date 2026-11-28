"""Produce register RTL materials from a new contract; never claim admission.

The primary RTL uses per-bit/per-byte updates. The alternative uses packed
bitmask updates. The eventual trusted checker must independently evaluate
observed protocol activity; agreement of these two RTLs is not an oracle.
"""
import argparse,hashlib,json
from pathlib import Path
from .contract import validate,obligations,FAMILY
from .verification import config_sv,anchors_sv,scenarios

PORTS='''module bridge(
 input logic clk,rst_n,psel,penable,pwrite,
 input logic [31:0] paddr,pwdata,input logic [3:0] pstrb,
 output logic [31:0] prdata,output logic pready,pslverr
);
'''

def rtl(c,packed=False,fault=None):
    validate(c);regs=c['registers'];n=len(regs)
    text=PORTS+'logic [31:0] value [0:%d];\ninteger waits;\ninteger target;\nlogic [31:0] lane_mask;\n'%(n-1)
    text+='always_comb begin\n target=-1;\n'
    for i,r in enumerate(regs):text+=" if(paddr==32'h%08x) target=%d;\n"%(r['address'],0 if fault=='alias' else i)
    text+=" lane_mask={{8{pstrb[3]}},{8{pstrb[2]}},{8{pstrb[1]}},{8{pstrb[0]}}};\n"
    text+=' prdata=(target<0)?0:value[target];\n'
    text+=' pslverr='+('0' if fault=='no_error' else '(target<0)')+';\n'
    text+=' pready=rst_n && psel && penable && (waits>=%d);\nend\n'%(0 if fault=='no_wait' else c['wait_cycles'])
    text+='always_ff @(posedge clk) begin\n if(!rst_n) begin\n waits<=0;\n'
    for i,r in enumerate(regs):text+=" value[%d]<=32'h%08x;\n"%(i,0 if fault=='bad_reset' else r['reset'])
    text+=' end else begin\n if(!psel || !penable || pready) waits<=0;else waits<=waits+1;\n'
    text+=' if(psel && penable && pready && pwrite) begin\n case(target)\n'
    for i,r in enumerate(regs):
        mode=r['access'];mask=r['write_mask']
        if mode=='ro' and fault!='ro_write':continue
        if mode=='ro':mode='rw';mask=0xffffffff
        if mode=='w1c' and fault=='w1c_rw':mode='rw'
        if fault=='reserved_write' and mode=='rw':mask=0xffffffff
        if packed:
            enable="32'hffffffff" if fault=='ignore_strobe' else 'lane_mask'
            maskexp="(%s & 32'h%08x)"%(enable,mask)
            expr='value[%d] & ~(pwdata & %s)'%(i,maskexp) if mode=='w1c' else '(value[%d] & ~%s) | (pwdata & %s)'%(i,maskexp,maskexp)
            text+=' %d:value[%d]<=%s;\n'%(i,i,expr)
        else:
            text+=' %d:begin\n for(integer bitnum=0;bitnum<32;bitnum=bitnum+1)\n'%(i)
            text+=" if((%s) && ((32'h%08x >> bitnum) & 1))\n"%('1' if fault=='ignore_strobe' else 'pstrb[bitnum/8]',mask)
            expr='value[%d][bitnum] & ~pwdata[bitnum]'%i if mode=='w1c' else 'pwdata[bitnum]'
            text+=' value[%d][bitnum]<=%s;\n end\n'%(i,expr)
    return text+' default:begin end\n endcase\n end\n end\nend\nendmodule\n'

def spec(c):
    s='''# Finite APB4 register bank

Implement `bridge.sv` using the declared interface. This module is an APB4 slave,
not an AXI bridge. One clock; active-low synchronous reset sampled at rising edges.
The environment asserts reset only while idle, holds it for at least two rising
edges, and starts the next Setup after reset is released. Reset during a pending
transfer is outside this task. No clock crossing, bursts or sideband protection
semantics are required. PADDR and PWDATA are32bits; PSTRB has4byte enables.

A transfer completes only at a rising edge with PSEL, PENABLE and PREADY high.
The master follows Setup/Access and holds address, direction, data and strobe
until completion. No requirement applies to PRDATA/PSLVERR outside Access.
PREADY must be low in reset, idle and Setup. During each Access there must be
exactly **WAIT** rising edges with PREADY low, followed by completion. Reset
restores the words below. Writes change state only on completion.

| Exact byte address | Reset word | Write mask | Access |
| --- | --- | --- | --- |
'''.replace('**WAIT**','**%d**'%c['wait_cycles'])
    for r in c['registers']:s+='| `0x%08x` | `0x%08x` | `0x%08x` | %s |\n'%(r['address'],r['reset'],r['write_mask'],r['access'].upper())
    return s+'''
For RW, enabled writable bits take PWDATA. For W1C, a one in PWDATA clears
an enabled writable bit; a zero preserves it. A bit is enabled only when its
byte PSTRB is1 AND its write-mask bit is1. All other bits retain their prior
value, including reserved bits set by reset. RO writes complete successfully
and preserve the value. Reads return the complete current32-bit word; PSTRB
has no effect on reads. All mapped accesses return PSLVERR=0.

All addresses other than the exact table entries, including unaligned
addresses, complete after the same wait count with PSLVERR=1 and PRDATA=0;
writes to these addresses change no state. Registers are independent. The
next request may start in the immediately following Setup cycle.

The submission is one self-contained synthesizable module with the fixed interface.
No external modules, compiler directives, hierarchy access, initial/final blocks,
assertions, delays, system tasks or file/network operations are allowed.

Deliver only `bridge.sv`; do not modify the specification, trusted checks,
references or inputs. Public development results and final evaluation are
separate. Candidate production alone does not grant industrial admission.
'''

def generate(c,out):
    validate(c);out=Path(out)
    if out.exists():raise ValueError('Never overwrite a generated candidate')
    out.mkdir(parents=True)
    def save(name,value):
        p=out/name;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(value if isinstance(value,str) else json.dumps(value,indent=2)+'\n')
    save('contract.json',c);save('spec.md',spec(c))
    save('workspace/bridge.sv',PORTS+"assign prdata=0;assign pready=0;assign pslverr=0;\nendmodule\n")
    save('fixtures/reference.sv',rtl(c));save('fixtures/reference_packed.sv',rtl(c,True))
    defects=['alias','ignore_strobe','no_error','bad_reset']
    if c['wait_cycles']:defects.append('no_wait')
    if any(r['access']=='w1c' for r in c['registers']):defects.append('w1c_rw')
    if any(r['access']=='ro' for r in c['registers']):defects.append('ro_write')
    if any(r['access']=='rw' and r['write_mask']!=0xffffffff for r in c['registers']):defects.append('reserved_write')
    for fault in defects:save('fixtures/bad_'+fault+'.sv',rtl(c,fault=fault))
    save('obligations.json',obligations(c))
    save('verification/register_config.svh',config_sv(c));save('verification/oracle_anchors.svh',anchors_sv(c))
    save('verification/tb.sv',Path(__file__).with_name('tb.sv.in').read_text())
    save('verification/public.vec',''.join('%d %08x %08x %x\n'%tuple(x) for x in scenarios(c)))
    save('task.json',dict(task_id=c['task_id'],family=FAMILY,delivery='rtl_implementation',editable=['bridge.sv'],
        qualified_resources_required=['apb4_active_master_32'],references=['fixtures/reference.sv','fixtures/reference_packed.sv'],
        negative_controls=['fixtures/bad_'+x+'.sv' for x in defects],status='materials_only_not_industrially_admitted',
        incomplete=['industrial execution and controls','runtime admission']))
    files={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob('*')) if p.is_file()}
    m=dict(schema='apb-register-materials-v1',task_id=c['task_id'],family=FAMILY,files=files,
           producer_files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),Path(__file__).with_name('contract.py'),Path(__file__).with_name('verification.py'),Path(__file__).with_name('tb.sv.in'))},
           status='candidate_materials_only',industrial_admission=False)
    save('manifest.json',m);return m

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('contract');p.add_argument('out');a=p.parse_args()
    print(json.dumps(generate(json.loads(Path(a.contract).read_text()),a.out),indent=2))
