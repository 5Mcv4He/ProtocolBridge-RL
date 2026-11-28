# 由地址契约生产候选，而非复制固定 Task ID

本目录将已有路由生产器、字对齐窗口契约和响应归属检查装配成可恢复的小批生产入口。研究者可以提供新的三个地址窗口；生产链生成 Spec、初始 RTL、两种合法结构、适用错误对照、验证场景、独立检查和来源清单。**生成成功不等于工业准入，更不等于已进行模型校准。**

## 支持的工程域

接口固定为 32-bit AXI4-Lite Slave 到三个 APB4 Master 目标，全局最多一笔未退休事务。窗口是互不重叠的四字节对齐区间，长度 4–16384 字节。局部 APB 地址为全局地址减去目标基址。其他边界由[契约检查](../router_v4/contract.py)明确拒绝，不进行无条件参数笛卡尔积。

例如，窗口 `[0x100c, 4100]` 从页内偏移 12 开始、跨越页边界。仅保留地址低位会给出错误的局部地址。因此该契约需要新的边界激励、独立地址归属锚点和丢失基址低位的错误对照；它不是改变随机种子。

现有错误银行还要求地址别名见证能够独立区分目标。某些不重叠布局仍会因此被拒绝，含义是“当前生成器的验收域不支持”，不是“工程上不可实现”。[空间分类器](../router_space.py)进一步区分不合法协议组合、尚未资格验证的角色和缺少专用判据的能力。

## 最小生产路径

从仓库根目录运行。输出放在忽略的私有目录；商业工具、VIP 和执行配置由使用者合法提供。

```python
# 保存为本地生产计划构造脚本；生产器本身无需增加 Task ID 分支。
import json
from pathlib import Path
from task_families.router_v6.batch import BASE_COMMIT, DEPENDENCIES, ROOT, sha

plan = {
    "schema": "word-owner-production-v1",
    "base_commit": BASE_COMMIT,
    "producer_files": {f: sha(ROOT / f) for f in DEPENDENCIES},
    "contracts": [{
        "task_id": "x2p_router_example_v1",
        "windows": [[0x100c, 4100], [0x5000c, 16], [0x8001000c, 64]],
        "purpose": "Exact local address across a page and independent small target boundaries."
    }],
    "limits": {"max_candidates": 1, "minimum_free_bytes": 2 * 1024**3}
}
Path(".local/router-plan.json").write_text(json.dumps(plan, indent=2))
```

```sh
python3 -m task_families.router_v6.batch \
  .local/router-plan.json .local/router-production
```

每个候选有 source、execution 与 package 三份来源阶段，以及静态测试记录。最终 package 的清单绑定实际执行文件。恢复同一批次时只核对已完成候选，不覆盖它们；改变计划或源码会拒绝恢复。中途留下的不完整候选需要明确审查，不能默认为生成成功。

## 功能对照与运行准入是两个入口

[工业批处理](qualify_batch.py)读取 `selected-router-controls-v1` 计划：`packages` 是绝对路径与实际 manifest SHA-256 的列表，另有有限 `budget_seconds` 和来源选择记录的 `selection_sha256`。它按序执行每个实例的真实控制银行，验证完成记录、输入、工具链及评分重放；编译失败或环境失败不能计作功能错误检出。

```sh
python3 -m task_families.router_v6.qualify_batch \
  .local/selected-controls.json .local/config.json .local/industrial-controls
```

工业入口的结果刻意保持 `admitted=false`：它只完成实例功能层。当前可运行池还由[分层准入](../../environment/package_admission_v3.py)要求严格匹配的运行机制证据、完整公开/终局/保留输入和执行环境。随后使用[任务池入口](../../environment/package_pool_v2.py)、[批量原生运行器](../../environment/native_tools/package_batch_v2.py)及[v10 导出](../../scripts/package_exchange.py)。不接受任意第三方可执行任务包；清单完整性不等于来源安全。

## 第二轮选择实际利用了什么？

[select_v2](select_v2.py)使用已完成工业对照的耗时、已确认的响应归属分类问题和新契约标签，选择有限工业样本。输入白名单排除模型成功率与保留结果；费用估计为已观察最大耗时加 10%，实际运行另有时间和空间上限。

先前 select 版本把“两个窗口相隔一个字”直接记作未映射间隙；第三个窗口可能占用该位置。v2 在工业执行前修正了这一标签判断，保留旧选择记录。标签用于选择有差异的任务，不替代实际测试、覆盖和错误对照。

当前状态：20 个第二轮候选已生成并经过静态检查；其中预先选定的三份已通过[实际工业对照与来源匹配准入](../../experiments/task-space-v1/production/word-controls-v1/manifest.json)，其余 17 份仍是未工业验收的候选。每份执行两种合法结构各 27 个完整及 22 个公开 case，并实际拒绝 17 个功能／时序错误对照。不能按候选数计为已准入。两份第一轮契约经过更新验证器重新准入后的真实模型结果见[生成任务校准报告](../../docs/generated-task-calibration.md)。新字对齐域的模型难度仍待校准。
