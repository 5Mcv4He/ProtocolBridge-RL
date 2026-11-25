# 固定模型批量研究：执行契约

本研究复用 revision 3、Policy v1 的权限与预算以及严格的单对象动作解析。原始失败动作不拆分、不修补。不是模型参数训练。历史 v1 数据不混入新批次。

当前 DSH 0.2.2rc2 高层 SDK 接口未发现自定义工具 schema/回调注册入口；其 patches 配置不等于已验证的安全工具注册机制。模型 API 本身支持 [Tool Calls](https://api-docs.deepseek.com/guides/tool_calls/)，但本轮未将其直接接入或声称完成原生工具调用验收。继续测量文本协议的实际合规性。

独立求解预先冻结十轮输入与轮换组序，先执行前三轮（9 次）。每组相同模型别名及 SDK 参数；temperature/seed 仍为 provider 默认值。每试次最多20动作；C/E最多2次公开调用。独立会话与工作区，单并发。预算默认最多30试次、已完成试次累计4小时、200万实际SDK Token；时间及Token在试次边界检查，因此最后一个试次可超出阈值，货币成本未知。每次启动前要求至少4GiB可用磁盘。

预实验质量门槛在结果前确定：全轨迹审计通过；无基础设施失败；9次完整保留；因格式错误且无有效编辑的试次少于1/3；格式错误动作比例不超过30%。门槛失败则停止扩大到30次，不删除模型失败。门槛通过也需按实际成本及剩余资源检查扩容是否可行。

远端任务通过可信 supervisor 脱离 SSH 会话，凭据只经标准输入和进程内存传递。每个任务目录只能首次创建，重复请求不启动第二次执行。客户端恢复同一冻结清单，已取得完成结果不会重跑或重新评分；仍运行的远端任务只继续观察。确认异常退出且无完整指标时保留失败封套和原始目录；存活状态不明时停止，不自动重跑。恢复不会清理运行中的编译目录。下载先进入临时目录，完整取回后改名。

```bash
python3 -m environment.policy_experiment --out .local/study-new --repeats 10 --limit 9
python3 scripts/batch_analysis.py .local/study-new --limit 9
# 质量、资源和成本检查通过后，保持原清单继续；不会重做前9次
python3 -m environment.policy_experiment --out .local/study-new --repeats 10 --limit 30 --resume
```

配对修复是独立的 `repair-v1` 研究：显式记录初始失败 RTL SHA-256，C/E使用相同修复提示；要求读文件后先test，才允许edit/submit。这次test占原有两次预算，拒绝动作也占20次额度。此约束不会施加到独立求解或历史Policy v1。若模型仍未取得反馈或未进行编辑，应记录并判定该试次未进入有效修复过程，而非人为替它修改。

```bash
python3 -m environment.policy_experiment --out .local/repair-new \
  --policies test_verdict,test_diagnostic --repeats 3 --limit 6 \
  --starting-rtl PATH_TO_CONFIRMED_AGENT_FAILURE.sv
```

分析使用全部启动试次为主分母，null单独列出；无有效编辑、不提交、协议错误均保留。失败标签允许重叠，不能将其相加当成互斥总数。Wilson区间是小样本描述，不支持因果排名。实际反馈曝光、反馈后编辑与最终奖励分别统计，不以允许test推断使用反馈。

新增计时仅包装原grader的subprocess调用，不改命令、激励或判定。compile/simulate wall time包含对应shell及日志读取开销；复用编译计为I/O，不冒充新编译。模型会话跨度包含等待公开EDA测试，不能称为纯模型推理时间。原始SDK Token与EDA日志保存在可信侧。
