# APB 主动激励角色探针

已有 X2P 使用 AXI 主端发请求、APB 从端响应。APB 主动 Master 是不同的资源角色：它可以直接激励自建 APB 设备，从而支持寄存器控制等新的工程对象。厂商提供该接口，不等于项目已经完成角色资格验证。

本探针使用自建的单寄存器对象，检查六笔真实事务中的字节写入、读回、两拍 Access 等待和未映射错误响应。预期值由接口检查器独立列出，不读取 DUT 内部存储，也不以“没有 UVM 错误”单独判断有效执行。三个受控行为错误分别丢失字节使能、跳过等待和抹掉错误响应。

**当前状态：修订版已通过真实角色验收。** [证据](../../experiments/task-space-v1/resources/apb-master-v2.json)确认合法对象完成六笔事务、十二个等待边沿，三种针对性错误均被功能／时序检查拒绝；整项探针耗时约 39.8 秒。第一版把响应同时驱动到 VIP 已有内部连接的顶层接口，产生多驱动，编译失败且未进入功能仿真。原始 [probe.sv](probe.sv) 保留，[probe_v2.sv](probe_v2.sv) 改接从端子接口，设备行为与独立检查不变。

该证据只资格化这个有限主动角色和六笔交互；不构成完整任务、任意寄存器语义验证或 Agent 求解证据。商业 VIP 和工具均由合法本地环境外部提供，仓库不包含其实现。

探针必须与其他商业工具批次串行运行。新的任务生产组件可以引用该有限角色，但必须另外验收自己的设备语义、边界、合法与错误对照，不能继承探针的判定结果。

<details>
<summary>在已授权的本地工具环境中复现四个对照</summary>

令 `PB_EDA_ENV` 指向本机统一环境入口，`PB_APB_VIP` 指向已生成的 APB VIP 包（包含 `include/sverilog` 与 `src/sverilog/vcs`）。它们是本机配置，不属于任务契约。先在项目根目录保存源码绝对路径，再进入全新的私有构建目录：

```bash
set -e
source "$PB_EDA_ENV"
probe_source="$PWD/verification_components/apb_master_v1/probe_v2.sv"
mkdir .local/apb-role-replay
cd .local/apb-role-replay
timeout 600 vcs -full64 -sverilog -ntb_opts uvm -timescale=1ns/1ps \
  +define+SVT_APB_MAX_DATA_WIDTH=32 +define+SVT_APB_MAX_ADDR_WIDTH=32 \
  +define+SVT_APB_MAX_NUM_SLAVES_1 +define+UVM_DISABLE_AUTO_ITEM_RECORDING \
  +incdir+"$PB_APB_VIP/include/sverilog" \
  +incdir+"$PB_APB_VIP/src/sverilog/vcs" "$probe_source" -top tb -o simv
for fault in 0 1 2 3; do
  timeout 60 ./simv +UVM_VERBOSITY=UVM_NONE +UVM_MAX_QUIT_COUNT=1 \
    +fault="$fault" > "fault-$fault.log" 2>&1
done
```

合法对象必须出现 `PB_ROLE_DONE transfers=6 waits=12`，且 UVM error/fatal 为零。三个负例必须分别实际触发 `PB_FUNCTION` 或 `PB_TIMING`；仅有非零退出、编译失败或超时不能算检出。UVM 主动停止可能仍返回进程退出码零，因此必须核对日志中的工程判据。上述调用范围与实际证据一致，不自动将新的工具版本视为已资格验证。

</details>
