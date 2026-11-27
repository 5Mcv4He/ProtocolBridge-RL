# 001 revision 3：配置、复现与证据重放

这是 001 revision 3 的历史复现手册，以下版本与部署示例保留其原始适用范围。当前项目先从[任务目录](task-catalog.md)选择执行路径；六个有限工程契约使用[独立运行说明](tasks/README.md)，不使用本页的 bridge.sv 假设。历史基线检查只核对已保存源码和证据，不代表重新完成 RTL 仿真。

[架构](architecture.md) · [真实 Agent 与奖励](agent-workflow.md) · [验证计划](verification-plan.md) · [评估报告](../mvp-evaluation-report.md)

新增固定模型 A／C／E 对照请使用 [Policy 实验运行说明](observation-policy.md)。以下旧入口与 revision 3 验收保持兼容。

所有命令在仓库根目录执行，输出目录必须尚不存在。运行使用 VCS / AMBA SVT；不使用 Icarus。商业安装、许可和 API key 由使用者自行准备，不随仓库发布。

## 1. EDA 环境

已使用的工具：VCS V-2023.12-SP2、AMBA SVT R-2020.12、UVM 1.1d。UTM 的 shell 初始化文件需配置 VCS 和许可。宿主 Python 3.6 可执行控制器，Mac 启动端使用 Python 3；DSH 用户态使用 Python 3.10。

在有许可的 Linux 内生成 VIP 项目：

```bash
bash environment/setup-vip.sh /your/new/generated-projects
```

复制 `environment/config.example.json` 到 `.local/config.json`，填写自己的 SSH 配置、运行目录、APB/AXI 生成项目目录和 VIP 安装目录。`PB_CONFIG` 可以指定另一份绝对路径配置。`compile_cache` 是可选 VCS 编译缓存，不能代替源码哈希检查或最终重新仿真。

## 2. 在 UTM 安装 DSH

为兼容现有 CentOS 用户态，使用 Ubuntu Base 22.04 amd64 的独立根文件系统。安装脚本需要可信宿主用户可 `sudo -n`，并检查本机 UID 1101、GID 1000 与目录没有冲突。默认路径仅是安装约定，不是密钥或许可位置。

1. 从 [Ubuntu 官方发布目录](https://cdimage.ubuntu.com/ubuntu-base/releases/22.04/release/)取得 `ubuntu-base-22.04.5-base-amd64.tar.gz` 与 `SHA256SUMS`，核验 SHA-256。
2. 把归档和本仓库的 `environment/` 脚本送到 UTM。
3. 在 UTM 执行：

```bash
bash environment/setup_utm_runtime.sh /path/to/verified-ubuntu-base-archive.tar.gz
```

脚本将 SDK / Runtime 0.2.2rc2 安装进 `/opt/protocolbridge-runtime/opt/dsh`，安装 root-owned launcher，创建低权限 solver 用户，并运行隔离探针。已有但不带本项目管理标记的根目录会被拒绝覆盖。首次安装需要网络；后续 API 请求也需要网络。

真实 API 探针与完整 Agent 试次是不同证据。仅成功安装、打印版本或跑隔离探针，不能声称完成 Agent 解题。

## 3. 标准基线检查与人工迭代 RTL

先运行 `python3 -m environment.check_baseline`。它核对当前运行源码、Spec、已保存结果及轨迹的哈希和验收条件，不执行新的 EDA 仿真。`reproduce.sh` 会先执行这项检查，再运行真实 VCS 回归。修改验证契约必须建立明确的新版本、新验收目录与证据；原 revision 3 的 `baseline.json` 和历史结果保持不变，不能刷新旧哈希来授予新源码准入。

```bash
python3 -m environment.reset .local/solve-001
# 编辑 .local/solve-001/bridge.sv
python3 -m environment.test .local/solve-001 .local/public-001
python3 -m environment.submit .local/solve-001 .local/submission-001
```

公开集 17 个 case、132 笔计划事务，含 8 笔复位取消。完整默认回归 22 个 case、2868 笔计划事务，含 26 笔复位取消。CLI `submit` 使用可复现的完整默认输入；它用于本地验证，不应被称作保密评测。

输出 `result.json` 记录 Reward、分类、每个实际执行的 case 和计数。提交结果位于 `submission-001/grade/result.json`。遇到首个确定错误会停止，不能将未运行 case 算成已通过。

## 4. 统一正反回归与真实 Agent

```bash
# 参考 + 10 个明确违反 Spec 的实现
bash environment/reproduce.sh .local/reproduction-001

# 从自己的密钥管理方式向当前进程提供 DEEPSEEK_API_KEY 后：
bash environment/reproduce.sh .local/reproduction-002 --agent

# 仅发起一个新的真实 Agent 试次；Mac 不需要安装 DSH
python3 -m environment.agent .local/agent-001 --model deepseek-flash
```

真实试次会把原创运行源码部署到 UTM 的私有 evaluator 目录，生成并冻结奖励／保留评估输入，随后在隔离 worker 内调用 DSH。密钥通过 SSH stdin 传递。不要把密钥写进配置文件、命令参数或 Git。

每个试次至多 20 次模型动作；模型可修改、测试、再修改、提交。终局提交后停止 solver，再对同一份 RTL 执行保留评估。结果保存到本地试次目录的 `run/`：

| 文件／目录 | 内容 |
|---|---|
| `result.json` | episode Reward、模型、轮数、冻结检查及保留评估摘要 |
| `freeze.json` | 运行源码与私有输入哈希 |
| `trace.json`、`harness-*.json` | 工具轨迹及真实 DSH 响应 |
| `candidate-*.sv` | 每次编辑的 RTL |
| `public-*/` | 每次公开测试 |
| `submission/` | 最终 RTL 快照和私有奖励验证 |
| `reserved-evaluation/` | 独立保留评估 |

私有具体输入仅留在可信 UTM evaluator 目录。`deployment.json` 记录其部署位置；不能上传它来泄露机器路径。每轮模型运行有随机性和 API 成本。

## 5. 不调用模型的复现与诊断

```bash
# 完整默认回归：可重放任意符合 Spec 的提交
python3 -m verifier.grade fixtures/reference.sv .local/reference-001

# 单个 case 只用于诊断，不能替代完整验收
python3 -m verifier.campaign fixtures/reference.sv .local/random-diagnostic --case random_stream_0

# 自定义可重复随机 seed（Python API）
python3 - <<'PY'
from verifier.campaign import grade
grade('fixtures/reference.sv', '.local/seed-12345', seed=12345)
PY

# 评分器与场景生成器自身的单元检查；不是 RTL 验证证据
python3 -m unittest discover -s tests -v
```

受信任的 UTM 操作者可用 `--cases-file /private/path/reward.json` 重放某次真实试次的原输入，私有文件不交给 solver。VCS 的内部 seed 固定为 17；测试输入的随机性来自 `scenarios.py` 的种子化生成。UVM sequence 用这些输入实际驱动商业 VIP，不存在 Python 替代 DUT 的仿真。

最终编译产物复用需候选和验证 SV 哈希完全一致，并复制到新的运行目录。修改设计后不能复用旧仿真结果。已确认功能错误给 0；工具中断、许可问题和验证不完整给 null。

## 6. 发布什么

只导出经过审阅的原创源码、说明、结果和精简轨迹：

```bash
python3 scripts/export_v3.py .local/reproduction-001/controls \
  experiments/industrial-v3 --agent .local/agent-001/run
```

导出器不上传商业编译／仿真日志、私有向量、SDK 安装包、许可或密钥。完整本地证据由哈希关联。旧 128 笔版本已从当前交付删除，不再提供兼容入口。
