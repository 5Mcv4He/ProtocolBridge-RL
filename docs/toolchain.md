# 工具与验证能力：哪些已具备，哪些需要补齐

本页解释工具用途。当前 v3 正在实机验证，最终验收以评估报告和证据为准。

[项目入口](../README.md) · [功能与场景计划](verification-plan.md)

| 能力 | 具体含义 | 工具／条件 |
|---|---|---|
| 工业 VIP 仿真 | 在具体激励下检查协议、事务与时序 | 已有 VCS V-2023.12-SP2、AMBA SVT R-2020.12 |
| Agent 在 UTM 内执行 | DSH Runtime、SDK 和 API 请求均发生在 UTM 内 | 已安装 SDK/Runtime 0.2.2rc2，Ubuntu 22.04 用户态、Python 3.10；真实 API 探针已成功 |
| Agent OS 隔离 | 限制求解进程能访问的文件、进程和权限 | 使用独立低权限 UID、chroot、mount/PID/IPC namespace、no_new_privs；已做负向访问探针 |
| 私有测试 | 具体输入不进入求解工作区，提交后由外部控制器调用 | 需要独立存放输入、冻结版本及受控反馈；不需要另买 EDA 工具 |
| 事务中复位 | 在请求半包、APB Setup/等待、AXI 响应背压阶段取消并恢复 | 需要激励、VIP 取消通知处理和复位感知 Scoreboard；用现有 VCS/VIP 实现 |
| 计划内覆盖闭合 | 每个需求有检查器，必要场景／交叉 bin 实际命中，缺口有解释 | 主要是验证工程；不等于穷尽所有状态或代码覆盖 100% |
| RTL 综合 | 将 RTL 转换为逻辑网表，检查可综合性与结构 | 尚未发现独立 Design Compiler；映射及面积／时序评估还需标准单元库和约束 |
| 形式属性验证 | 在明确的环境假设下证明性质，或得到反例 | 需要可用的 VC Formal FPV 及许可，另需编写假设／性质、检查 vacuity 和 proof 状态 |
| 形式等价检查 | 比较 RTL 与综合网表等两个设计是否等价 | Formality 等工具；用途不同于 FPV |

## 工具版本选择

这项单时钟协议桥不要求 DC/VC Formal 与 VCS 精确同版本。为了配合现有 CentOS 7.9，优先核对 2023.12 系列 Linux x86-64 安装包及产品 Release Notes；这是兼容性优先的建议，不是功能最低版本。

Synopsys 的[平台路线图](https://www.synopsys.com/support/licensing-installation-computeplatforms/compute-platforms/compute-platforms-roadmap.html)列出该时期对 CentOS 7.3+ 的支持，同时明确具体产品／平台需以下载中心为准。不能推断所有更新版本都兼容现有系统。

准备 DC 时，需要可用的综合许可；若要映射标准单元，优先提供 `.db` 库。若只有 Liberty `.lib`，还要确认库转换工具。准备 VC Formal 时，明确需要 FPV 能力／许可。[官方说明](https://www.synopsys.com/glossary/what-is-equivalence-checking.html)区分了 Formality 等价检查和 VC Formal 的属性验证等应用。

目前在 VCS 安装内发现 `vcfca/vc_static_shell`，但一次限时探针未完成，尚不能确认它可执行独立 FPV。可执行文件存在、`-help` 可用和有效许可证签出是不同证据。

## 隔离与证明的边界

Agent 的隔离探针已确认低权限 UID、进程命名空间、不可见宿主 home／评分器目录、不可改写 worker 程序、无有效 capabilities、禁止提权。网络仍用于调用模型服务；这不是完整的网络沙箱。多个试次目前共用该低权限 UID 和根文件系统，因此尚未实现试次之间的 OS 文件隔离；允许的 Agent 工具仍只读取当前试次的两份任务文件。

候选 RTL 另有受限语法检查和执行超时。当前不能把这些描述为已完成恶意编译器输入审计或所有形式的沙箱逃逸防护。

形式验证也不是“装好工具就证明正确”。必须逐条报告 proven、failed、bounded、inconclusive，说明输入假设和覆盖／非空性；综合通过也不证明协议功能正确。这些能力可以补齐，但各自需要真实运行证据。
