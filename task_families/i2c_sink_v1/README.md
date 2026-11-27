# 有限 I²C 写入任务族

本任务族把串行接收与事务局部组字区分为 byte、word 两份契约。规格边界与执行方法见[任务指南](../../docs/tasks/i2c-write-sink.md)。

当前生成入口是 [generate_v2.py](generate_v2.py)，当前门禁是 [quality_v2.py](../../verifier/i2c_sink/quality_v2.py)。[qualification.py](qualification.py)要求规范生成包与已通过的源文件证据严格匹配。生成器不能自行授予准入。

`generate.py` 和旧 `quality.py` 为被拒绝的初版保留：word 分支曾生成不能编译的 RTL，功能反例的子项判定又只核对奖励值。修订 2 修正词法分隔，并要求功能／时序反例以相应失败类别被检出。旧版本只用于核查[原始拒绝证据](../../experiments/i2c-sink-v1/quality-rejected-v1.json)，不应作为当前生产入口。

两种契约不支持完整 I²C 控制器行为，也不按随机输入或重复导出增加任务数量。
