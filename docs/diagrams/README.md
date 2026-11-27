# README 架构图

原有八张架构 SVG 与新增的奖励分布示意图均为可维护的静态源文件，与首页章节对应，手工设计节点、层级、连线及留白。统一 760 单位宽度、圆角和低饱和度颜色：蓝色用于核心架构、任务及奖励，绿色用于执行与工具交互，灰色用于控制和基础设施，琥珀色用于错误对照。虚线表示独立作用域或尚未接入的关系，以图中标签为准。

SVG 内含系统深色偏好样式，不支持时仍可使用浅色画布；不依赖脚本、外链字体或第三方图片服务。每张图保留 title / desc 与 README 替代文本。后续更新时同步核对图中的能力与状态，不将计划画成已实现，不修改冻结实验或任务契约。

新图与文档的叙事、图形语义、配色数值及渲染验收见[文档设计规范](../documentation-guidelines.md)。复用现有样式，不机械复制布局；此目录保存图源，临时预览留在本地。

新增 [reward-distribution.svg](reward-distribution.svg) 用于说明二值奖励的组内差异，数据为明确标注的示意，不是实测分布；其绿色和灰色单元分别表示 1 和 0，数字标签同时承担含义。实际成功率仍以研究报告为准。

[task-family-production.svg](task-family-production.svg) 用于解释有限任务族从契约特化、候选检查、工业准入到真实求解的责任边界。它复用同一配色与字体；上排从左向右生产候选，下排从右向左经过检查与门禁，底部才启动模型求解。通过证据绑定源码与工具链，不能由生成器自授。

[queue-lifecycle-obligations.svg](queue-lifecycle-obligations.svg) 表达队列契约中的接受、APB 完成和响应退休三个事件，以及两条独立账目检查路径。图中是契约示意，不是实测波形；数量不一致与候选违例分别对应不可判定和功能失败。

[composed-route-retirement.svg](composed-route-retirement.svg) 表达路由与队列组合中的两条执行路径：映射请求访问选中 APB 目标，未映射请求形成 DECERR；两者都保持名额直到 AXI 响应退休。区域包含关系表示未退休生命周期，图为契约示意。

[verification-budget.svg](verification-budget.svg) 表达测试额度对照的固定条件、Agent 自主验证决策与提交后的评分边界。它是实验设计图，不是成功率或模型内部推理示意。


## 不同验收依据

[verification-bases.svg](verification-bases.svg)表达三类有限工程交付在提交冻结后的不同判据：UART 的工业解码与周期模型、激励任务的合法／错误设计区分、RTL 修复的独立参考等价。并排区域表示责任不同，不表示证明强度相同。对应[研究报告](../verification-resources-tasks.md)中的实际验收与限制；沿用蓝／绿／灰／琥珀的角色语义。

[返回首页](../../README.md)
