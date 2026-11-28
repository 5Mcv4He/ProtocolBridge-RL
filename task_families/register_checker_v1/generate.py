"""Two event-level register contracts derived from the existing device semantics.

This produces a checker task, not an RFFE serial-protocol implementation. No
trusted vector or oracle is generated from these RTL update expressions.
"""
import argparse,hashlib,json
from pathlib import Path
MODES=('rw','w1c')
HEADER='''module register_checker(input logic clk,rst_n,event_valid,is_write,
 input logic [3:0] address,input logic [7:0] write_data,read_data,
 output logic error);
'''
def reference(mode,alternate=False):
    if mode not in MODES:raise ValueError('Unsupported mode')
    reset="8'h00" if mode=='rw' else "8'hff"
    if alternate:
        # One independent process per register; delayed error is not permitted.
        return HEADER+'''logic [15:0] bad;
 assign error=|bad;
 genvar k;
 generate for(k=0;k<16;k=k+1)begin: cell_model
 logic [7:0] value;
 always @(posedge clk)begin
  if(!rst_n)begin value<='''+reset+''';bad[k]<=0;end
  else if(!error && event_valid && address==k)begin
   if(is_write) value<='''+('write_data' if mode=='rw' else 'value & ~write_data')+''';
   else if(read_data!=value)bad[k]<=1;
  end
 end
 end endgenerate
endmodule
'''
    return HEADER+'''logic [7:0] expected [0:15];integer i;
 always @(posedge clk) begin
  if(!rst_n)begin
   error<=0;
   for(i=0;i<16;i=i+1)expected[i]<='''+reset+''';
  end else if(!error && event_valid)begin
   if(is_write)expected[address]<='''+('write_data' if mode=='rw' else 'expected[address] & ~write_data')+''';
   else if(read_data!=expected[address])error<=1;
  end
 end
endmodule
'''
def controls(mode):
    s=reference(mode);reset="8'h00" if mode=='rw' else "8'hff"
    return {
      'always_accept':HEADER+'assign error=0;endmodule\n',
      'always_reject':HEADER+'assign error=rst_n;endmodule\n',
      'write_alias':s.replace('expected[address]<=','expected[address^1]<='),
      'read_alias':s.replace('read_data!=expected[address]','read_data!=expected[address^1]'),
      'ignore_upper_address':s.replace('expected[address]','expected[address & 7]'),
      'ignore_event_valid':s.replace('!error && event_valid','!error'),
      'wrong_update':s.replace('expected[address]<='+('write_data' if mode=='rw' else 'expected[address] & ~write_data'),'expected[address]<='+('expected[address] & ~write_data' if mode=='rw' else 'write_data')),
      'read_has_side_effect':s.replace('else if(read_data!=expected[address])error<=1;', 'else begin expected[address]<=0;if(read_data!=expected[address])error<=1;end'),
      'error_not_sticky':s.replace('end else if(!error && event_valid)begin','end else begin error<=0; if(!error && event_valid)begin').replace('\n end\nendmodule','\n end end\nendmodule'),
      'reset_keeps_state':s.replace('expected[i]<='+reset,"expected[i]<=expected[i]"),
      'miss_msb_error':s.replace('read_data!=expected[address]','(read_data & 127)!=(expected[address] & 127)')}

def generate(mode,out):
    if mode not in MODES:raise ValueError('Unsupported mode')
    out=Path(out);out.mkdir(parents=True,exist_ok=False);(out/'workspace').mkdir();(out/'controls').mkdir()
    meaning='复位值为0；写入替换该地址的完整字节。' if mode=='rw' else '复位值为255；写入中每个1清除相应位，每个0保持原位（W1C）。'
    spec='''# 寄存器观察结果检查器

一个监测器把串行设备的完整事务解码为每拍至多一个事件。你需要实现检查器，根据已经接受的写事件预测寄存器状态，判断后续读回是否符合规格。被检查的事件流可能含错误读回；检查器应报告错误，不能把所有事件都当作正确。

## 固定接口与采样

唯一模块 `register_checker`，端口依次为 `clk,rst_n,event_valid,is_write,address,write_data,read_data,error`。前四项及error为1位，address为4位，两个data为8位；前七项输入，error输出。所有输入均为二态，除clk外在上升沿前稳定；单时钟、低有效同步复位。第一次事件之前至少采样一次复位。

每个clk上升沿：rst_n=0具有最高优先级，忽略该拍事件，重置全部预测状态并清除error。否则，event_valid=0表示无事务，所有事务字段忽略。event_valid=1时，is_write=1为完整写事件，仅使用address与write_data；is_write=0为完整读事件，仅使用address与read_data。连续每拍事件合法，不需要空闲间隔。没有未完成请求、额外握手或同拍两个事件。

## 状态与判定

有16个独立字节寄存器，地址0–15均合法。'''+meaning+'''
读无副作用。读事件必须比较该上升沿之前、已经包含此前所有有效写事件的预测状态，不因错误读回修正预测值。写时read_data忽略；读时write_data忽略。

首次错误读回时，error必须在该上升沿更新后立即为1，不允许多延迟一拍。error保持1直到下一次复位；发生错误后的内部预测状态不作要求。复位后必须恢复正确检查，包括此前出错的地址。没有错误读回时error必须一直为0，不能误报合法输入。

例如W1C状态FF写01后为FE，再写02为FC；重复写02仍为FC。RW则每次写入直接成为新的预测值。仅本任务声明的模式适用，不能根据数据自动猜测模式。

## 边界与交付

只修改checker.sv，交付自包含可综合SystemVerilog。禁止参数、宏、include、initial、系统任务、文件或层次访问、外部模块及测试台。无串行引脚、奇校验、Bus Park或电气检查；这些属于设备实现任务。本任务测量事务状态建模、地址归属、复位及误报／漏报控制，不宣称覆盖RFFE协议本身。

可信侧分别提供合法和故意错误的事件流，用独立逐位状态模型检查每一拍的error。Agent的检查器是被评价对象，不能修改激励、判据和评分规则。完整检查通过reward=1；确认的输出违例或编译错误为0；无效提交、运行不完整或环境故障为null。公开反馈绑定当前源码；submit冻结并结束求解，终局与保留评估不返回模型继续修复。
'''
    task='register_checker_'+mode+'_v1'
    meta=dict(task_id=task,version=1,family='register-checker-v1',mode=mode,deliverable='checker.sv',verifier='verifier.register_checker.campaign',capabilities=['state-prediction','address-identity','write-overwrite' if mode=='rw' else 'write-one-clear','false-positive-negative-control','sticky-error-reset'],obligations=['all-addresses','each-data-bit','read-after-write','read-no-side-effect','ignored-fields','idle-no-update','back-to-back','first-error-same-cycle','sticky-until-reset','reset-dominates-active-event','address-times-update-times-reset'],source_origin='empty checker; all negative controls are synthetic',admission='candidate; no industrial admission implied')
    (out/'spec.md').write_text(spec);(out/'task.json').write_text(json.dumps(meta,indent=2)+'\n')
    (out/'workspace/checker.sv').write_text(HEADER+'assign error=0;endmodule\n');(out/'reference.sv').write_text(reference(mode));(out/'alternate.sv').write_text(reference(mode,True))
    for name,source in controls(mode).items():(out/'controls'/(name+'.sv')).write_text(source)
    (out/'README.md').write_text('# 寄存器检查器：'+mode+'\n\n从[规格](spec.md)理解“接受事件→预测状态→判断读回”的关系。Agent只修改[checker.sv](workspace/checker.sv)。此任务复用既有RFFE设备的有限寄存器语义，但不执行串行VIP，也不继承其准入证据。\n\n参考与错误对照属于可信侧；生成只是候选，实际准入由独立逐位模型和VCS逐拍比较确认。两个合法实现分别采用统一数组和按地址独立状态进程。\n')
    manifest=dict(schema='register-checker-generation-v1',task_id=task,generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),files={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob('*')) if p.is_file()})
    (out/'generation.json').write_text(json.dumps(manifest,indent=2)+'\n');return manifest
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=MODES);p.add_argument('out');a=p.parse_args();generate(a.mode,a.out)
