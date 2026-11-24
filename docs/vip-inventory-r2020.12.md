# R-2020.12 VIP 资源盘点（初步研究）

> **状态：50 包分发资源经本地 Agent 报告已完成存在性及基本数据完整性核查；具体能力与运行验收尚待验证。**
> 本文是 ProtocolBridge-RL 的第一项资源调研记录，不表示本地 EDA 运行、VIP 编译、验证功能或 RL 任务环境已经验收通过。

[2026-11-24 本地审计摘要](vip-audit-2026-11-24.md) 已记录 50/50 包的数据段可读取性、49 包共 58 份 release notes、五个重点包的文档能力，以及全部 VIP 尚未完成完整运行验收的证据边界。

## 研究目标与证据边界

梳理现有 R-2020.12 系列工业 Verification IP（VIP）的目录与协议定位，为后续确定可实现的协议转换任务、独立端到端语义模型、仿真验证器和可验证奖励提供候选池。

- **来源**：项目维护者提供的 R-2020.12 资源表。本表中的 `✅` 最初仅表示维护者报告资源存在；后续本地审计已报告 50/50 分发文件存在、与同目录校验表一致并可解析标准数据段，但尚未证明厂商真实性、授权、完整安装、版本兼容性或实际运行结果。
- **收录规则**：严格只收录 R-2020.12 列为 `✅` 的条目，共 **50 个目录／包条目**。`smartsearch` 在此列为 `—`，不计入（纠正先前 51 项的误计）。
- **定义限制**：目录名通常可提示协议类别，但不能独立证明特定协议版本、BFM 角色、sequence、checker、coverage、示例可运行性，也不等于 50 种独立协议。
- **发布边界**：本文仅列目录标识及协议的一般用途，不包含商业 VIP 的源代码、未授权资料、安装路径、许可证信息、原始运行日志或专有 sequence。

## 总览

| 分类 | 条目数 |
| --- | ---: |
| 片内总线与互连 | 3 |
| 通用外设、电源管理与调试 | 9 |
| 车载通信 | 3 |
| 高速互连与网络通信 | 6 |
| DRAM 与内存控制器接口 | 5 |
| 闪存与存储设备接口 | 7 |
| 显示、音频与数据采集 | 8 |
| USB 与相关接口 | 4 |
| 其他 MIPI 层次与集合 | 3 |
| 公共库与工具（尚未识别） | 2 |
| **总计** | **50** |

## 逐项资源清单

下列“协议定位／潜在任务”仅表示**行业通用概念和研究方向**，并非对该版本 VIP 具体能力的确认。目录名映射不确定时显式标为“待核”。

### 片内总线与互连

| 包目录 | 初步协议／接口定位 | 潜在 RTL / 验证研究方向 |
| --- | --- | --- |
| `amba_svt` | AMBA 总线协议家族（具体子协议待查） | 片内寄存器访问、主从事务和桥接适配 |
| `tilelink_svt` | TileLink 片上互连 | RISC-V SoC 访问、请求响应及协议适配 |
| `ocp_vrt` | OCP（Open Core Protocol，目录映射待核） | IP 核互连与事务接口适配 |

### 通用外设、电源管理与调试

| 包目录 | 初步协议／接口定位 | 潜在 RTL / 验证研究方向 |
| --- | --- | --- |
| `i2c_svt` | I²C 两线控制总线 | 寄存器读写、地址/ACK、时序状态机 |
| `mipi_i3c_svt` | MIPI I3C 传感器/控制接口 | 动态地址、控制命令及设备访问 |
| `spi_svt` | SPI 串行外设接口 | 时钟模式、片选、数据移位与控制器 |
| `uart_svt` | UART 异步串行通信 | 帧、波特率、校验、FIFO |
| `avsbus_svt` | AVSBus 电压调节控制接口 | 调压命令与控制应答 |
| `mipi_rffe_svt` | MIPI RFFE 射频前端控制 | 射频设备寄存器及控制事务 |
| `mipi_spmi_svt` | MIPI SPMI 电源管理接口 | PMIC 命令与状态控制 |
| `jtag_svt` | JTAG 测试访问/扫描接口 | TAP 状态机、指令/数据寄存器 |
| `swd_svt` | Serial Wire Debug 调试接口 | 请求/应答、线路换向和调试访问 |

### 车载通信

| 包目录 | 初步协议／接口定位 | 潜在 RTL / 验证研究方向 |
| --- | --- | --- |
| `can_svt` | CAN 车载总线 | 标识符、仲裁、帧和错误处理 |
| `lin_svt` | LIN 低速车载总线 | 主节点调度、帧头、响应与校验 |
| `flexray_svt` | FlexRay 车载通信 | 静态/动态时隙、同步和消息调度 |

### 高速互连与网络通信

| 包目录 | 初步协议／接口定位 | 潜在 RTL / 验证研究方向 |
| --- | --- | --- |
| `pcie_svt` | PCI Express 高速串行互连 | 请求/完成、TLP 事务、配置及流控 |
| `cxl_subsystem_svt` | Compute Express Link 子系统 | CXL 设备与协议子层；支持范围待查 |
| `ethernet_svt` | 以太网（具体 MAC/PHY/速率待查） | 帧收发、CRC、缓冲与流控 |
| `fc_svc` | Fibre Channel（目录后缀为 svc） | 存储网络帧与端口状态 |
| `intlkn_nvs` | Interlaken（目录映射待核） | 高速分组、通道复用和流控 |
| `cpri_svt` | CPRI 无线前传接口 | 采样数据映射、帧和同步 |

### DRAM 与内存控制器接口

| 包目录 | 初步协议／接口定位 | 潜在 RTL / 验证研究方向 |
| --- | --- | --- |
| `ddr_svt` | DDR SDRAM | 存储命令、地址、读写与时序 |
| `lpddr_svt` | 低功耗 DDR | 读写、刷新、低功耗和初始化 |
| `gddr_svt` | 图形 DDR | 高带宽数据访问和时序控制 |
| `hbm_svt` | 高带宽存储器 | 多通道/伪通道、bank 和命令 |
| `dfi_svt` | DDR PHY Interface | 内存控制器与 PHY 的数字接口 |

### 闪存与存储设备接口

| 包目录 | 初步协议／接口定位 | 潜在 RTL / 验证研究方向 |
| --- | --- | --- |
| `emmc_svt` | eMMC 嵌入式闪存接口 | 命令响应、块读写和状态 |
| `jedec_ufs_svt` | UFS 存储协议 | 请求、命令、存储事务和响应 |
| `nvme_svt` | NVM Express 存储接口协议 | 提交/完成队列与控制器命令 |
| `onfi_svt` | Open NAND Flash Interface | NAND 页/块操作及忙状态 |
| `tnand_svt` | 推定 Toggle NAND（待核） | NAND 闪存数字接口与时序 |
| `sas_svc` | Serial Attached SCSI（目录后缀为 svc） | SCSI 命令、链路与存储访问 |
| `sata_svc` | Serial ATA（目录后缀为 svc） | ATA 命令、数据链路和控制 |

### 显示、音频与数据采集

| 包目录 | 初步协议／接口定位 | 潜在 RTL / 验证研究方向 |
| --- | --- | --- |
| `dp_svt` | DisplayPort | 显示链路、音视频数据和辅助控制 |
| `hdmi_svt` | HDMI | 音视频数据和链路控制 |
| `mipi_dbi_svt` | MIPI Display Bus Interface | 显示命令、寄存器/图像数据更新 |
| `mipi_dpi_svt` | MIPI Display Pixel Interface | 像素流、行场同步及消隐 |
| `i2s_svt` | Inter-IC Sound | 多声道音频采样串行传送 |
| `mipi_slimbus_svt` | MIPI SLIMbus | 音频通道与控制消息 |
| `mipi_soundwire_svt` | MIPI SoundWire | 音频数据与设备控制 |
| `jesd204_svt` | JESD204 数据转换器接口 | ADC/DAC 采样、lane 映射与对齐 |

### USB 与相关接口

| 包目录 | 初步协议／接口定位 | 潜在 RTL / 验证研究方向 |
| --- | --- | --- |
| `usb_svt` | USB 数据通信协议家族 | 设备/主机端点与数据交互 |
| `typec_svt` | USB Type-C 连接与角色机制 | 连接检测、接口方向和角色管理 |
| `usb_pd_svt` | USB Power Delivery | 供电能力协商和控制消息 |
| `usb4_subsystem_svt` | USB4 子系统 | 路由、隧道、适配器与带宽管理 |

### 其他 MIPI 层次与集合

| 包目录 | 初步协议／接口定位 | 潜在 RTL / 验证研究方向 |
| --- | --- | --- |
| `mipi_svt` | 具体协议内容未知 | 必须查看本地 package/文档后再归类 |
| `mipi_unipro_svt` | MIPI UniPro | 可靠链路和传输，常与 UFS 协同 |
| `mphy_svt` | MIPI M-PHY | 高速串行物理接口与相关控制 |

### 公共库与工具（尚未识别）

| 包目录 | 初步协议／接口定位 | 潜在 RTL / 验证研究方向 |
| --- | --- | --- |
| `library19_svt` | 本地审计识别为含多个协议目录的资源集合（具体组成待深审） | 不是单一协议；后续核查其内容与依赖关系 |
| `vipcc` | 本地文档标识为 Configuration Creator；说明封面 Q-2019.12，实际运行版本未知 | 配置工具而非独立协议；后续核查运行入口、版本与依赖 |

## 待本地 Agent 采集的能力字段

除审计报告中已说明的 5 个重点包之**文档级有限能力**外，以下详细字段尚未建立本仓库可复核的运行证据。不得根据目录名、通用官网说明或其他发行版信息推断后自动填满。

| 字段 | 当前结论 | 建议证据 |
| --- | --- | --- |
| 分发文件可读取性 | 本地审计报告完成 50/50 基础检查；不等于完整安装 | 本地私有 CRC、解析和 SHA-256 记录 |
| 完整安装、精确发行版/build |  | 本地 release notes、manifest、组件索引及运行版本 |
| 支持的协议版本／子集 |  | 本地用户手册、示例配置、版本说明 |
| VIP 角色和数据交换层次 |  | package、example 入口、端口/接口/事务层配置 |
| BFM / Driver / Monitor |  | 类名、接口与示例连接（仅记录名称和证据位置） |
| 提供的 Sequence 及适用前提 |  | sequence list、示例或用户手册索引 |
| Assertion / Protocol Checker |  | 配置项、错误类别及可触发证明 |
| Coverage / Scoreboard |  | 功能覆盖定义、监视输出、是否含端到端比对 |
| Reference model / transaction API |  | 手册与示例所列的接口和用途 |
| 仿真器与 UVM 兼容性 |  | VCS 版本、官方兼容矩阵、许可状态（只记录脱敏状态） |
| 示例运行和负例检测 |  | 授权环境中的可重复执行结果及脱敏摘要 |
| 公开分发边界 |  | 本地许可／项目来源条款，由授权持有人审查 |

### 单包能力报告建议 Schema

```yaml
package: amba_svt
inventory_presence: reported_local_distribution_present  # 根据维护者提供的本地审计摘要，不是公开独立复核
local_release:
protocols: []
supported_versions: []
roles: []
interfaces: []
bfm: []
monitors: []
sequences: []
protocol_checkers: []
assertions: []
coverage: []
scoreboards: []
example_projects: []
simulator_compatibility:
smoke_status: not_run
negative_control_status: not_run
evidence_refs: []    # 私有审计记录中的证据 ID；不要公开专有文件路径
public_summary_allowed: unknown
notes:
```

## 对 ProtocolBridge-RL 的作用

资源盘点只是任务工厂的输入。后续应将**可证明的协议组合与行为映射**组织为任务家族：例如同类总线事务转换、外设寄存器控制、数据流适配、存储命令控制等。无法形成明确功能契约的两个协议不应随意配对。

VIP 的两端合规检查也不能代替跨协议语义正确性：每个任务仍需独立的事务映射 Oracle / Scoreboard、测试完整性检查，以及真实正确／错误对照。

## 下一步调查与验收

1. **只读盘点**：本地核实目录、版本、文档索引、组件及示例；生成私有证据索引和不含专有内容的公开摘要。
2. **能力确认**：逐包登记实际角色、事务层接口、Sequence、Checker、Coverage；不存在或无法确认时保持空白。
3. **最小运行验收**：在授权、兼容的环境中，对可选示例分别验证编译、运行、可观测 PASS，以及一项已知违规能否触发 Checker。
4. **任务适配性筛选**：仅对已确认的 VIP 功能提出候选任务及独立 Oracle 需求，避免把 VIP 内建 Sequence 无条件全部执行。
5. **质量审计**：将环境错误、设计错误和判分错误区分，保证奖惩无法被 DUT/Agent 修改的测试文件影响。

当前尚无经过实际运行验收的 50 包能力矩阵。2026-11-24 的分发清点与 5 个重点包文档能力结果另见[本地审计报告](vip-audit-2026-11-24.md)。后续将根据新的**脱敏运行证据**逐项更新。

---

本文描述研究状态，不包含任何厂商商业 VIP 源码、未授权序列或私有配置。
