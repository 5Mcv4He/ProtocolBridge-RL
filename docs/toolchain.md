# 工具与验证能力：哪些已具备，哪些需要补齐

本页解释工具用途与当前能力。历史 v3 的工具版本保持在原证据中；新实验以各自的 toolchain、freeze 和实际执行记录为准。[综合工具接口](synthesis-tools.md)中的自身网表等价独立于 X2P 功能 Reward；后续[独立参考修复任务](verification-resources-tasks.md)则使用 Formality 作为专用功能验收，两种比较关系不可混用。

[项目入口](../README.md) · [功能与场景计划](verification-plan.md)

| 能力 | 具体含义 | 工具／条件 |
|---|---|---|
| 工业 VIP 仿真 | 在具体激励下检查协议、事务与时序 | 历史 v3：VCS V-2023.12-SP2；后续任务实测：VCS-MX O-2018.09-SP2、AMBA SVT R-2020.12、UVM 1.2 |
| UART 发送器功能验收 | 工业 Monitor 解码与独立周期模型共同检查帧、输入锁存及 ready；范围仅 8N1／8E1 固定速率发送 | UART VIP R-2020.12、VCS O-2018.09-SP2；[当前修订 4 的 26 项准入检查](../experiments/verification-resources-v1/uart-quality-v4.json) |
| Agent 在执行后端内运行 | DSH Runtime、SDK 和 API 请求发生在隔离的 Linux 运行环境内 | SDK/Runtime 0.2.2rc2 已有真实试次；OS、Python 与客户端身份以各批次冻结记录为准，历史用户态配置不是任务要求 |
| Agent OS 隔离 | 限制求解进程能访问的文件、进程和权限 | 使用独立低权限 UID、chroot、mount/PID/IPC namespace、no_new_privs；已做负向访问探针 |
| 私有测试 | 具体输入不进入求解工作区，提交后由外部控制器调用 | 需要独立存放输入、冻结版本及受控反馈；不需要另买 EDA 工具 |
| 事务中复位 | 在请求半包、APB Setup/等待、AXI 响应背压阶段取消并恢复 | 需要激励、VIP 取消通知处理和复位感知 Scoreboard；用现有 VCS/VIP 实现 |
| 计划内覆盖闭合 | 每个需求有检查器，必要场景／交叉 bin 实际命中，缺口有解释 | 主要是验证工程；不等于穷尽所有状态或代码覆盖 100% |
| RTL 综合 | 将 RTL 转换为逻辑网表，检查可综合性与结构 | Design Compiler O-2018.06-SP1 已实际综合；受控 synth_check 与验收范围见[新报告](synthesis-tools-evaluation.md) |
| 形式属性验证 | 在明确的环境假设下证明性质，或得到反例 | 当前未验收 VC Formal FPV；尚无队列容量／仲裁属性证明 |
| 形式等价检查 | 比较 RTL 与综合网表等两个设计是否等价 | Formality O-2018.06-SP1：已验收自身网表等价与独立参考累加器修复；后者另有[15 项准入检查](../experiments/verification-resources-v1/independent-reference-quality.json)，二者均不同于 FPV |

## 工具版本与测量边界

新工具无需与历史 VCS 精确同版本；应使用实际正反例验收，而不是凭可执行文件、帮助输出或许可条目推断能力。DC、Formality、PrimeTime PX 的已发布流程证据使用 O-2018.06-SP1。这些特定流程证据不等于重新核验全部安装能力；最新资源核查及证据层次见[能力到任务的映射](verification-resources-tasks.md)。安装及许可配置由环境管理员维护，不是 Task 的组成部分。

PrimeTime 使用 `pt_shell` 的 averaged PX 流程。当前 `class.db` 是教学库：阈值与功耗表不完整，DBR-207 保留在记录中，internal/leakage 为零不代表真实功耗为零。面积、时序和功耗只作流程验证或固定条件下的相对测量，不进入现有功能奖励。Library Compiler 可作为未来换用经过验收的工艺库的准备路径；当前没有正式物理优化任务。

SpyGlass、ICC2、TetraMAX 等未接入当前已验收的 Agent 工具配置或奖励。程序、介质或授权条目的存在不能替代功能验收。

## 隔离与证明的边界

Agent 的隔离探针已确认低权限 UID、进程命名空间、不可见宿主 home／评分器目录、不可改写 worker 程序、无有效 capabilities、禁止提权。网络仍用于调用模型服务；这不是完整的网络沙箱。多个试次目前共用该低权限 UID 和根文件系统，因此尚未实现试次之间的 OS 文件隔离；文件读取动作受当前试次的材料白名单限制；支持 observe 等动作的 X2P 配置另经受控接口查询公开实验，不能任意读取日志或可信目录。六个有限契约的已发布配置仅开放 read/edit/test/submit。

候选 RTL 另有受限语法检查和执行超时。当前不能把这些描述为已完成恶意编译器输入审计或所有形式的沙箱逃逸防护。

形式验证也不是“装好工具就证明正确”。必须逐条报告 proven、failed、bounded、inconclusive，说明输入假设和覆盖／非空性；综合通过也不证明协议功能正确。这些能力可以补齐，但各自需要真实运行证据。
