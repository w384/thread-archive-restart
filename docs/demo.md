# 快速演示（Demo）

## 1. 测量所有线程

```bash
python scripts/measure_thread_context.py
```

输出示例（合成数据）：

```text
thread_id                              cum_input  turn_delta  last_usage  window    occ turns  flags
33333333-3333-4333-8333-333333333333   10,050,100         100          100  200,000    0%     3  ARCHIVE
22222222-2222-4222-8222-222222222222      250,000     250,000       50,000  200,000   25%     1  TRIGGER
44444444-4444-4444-8444-444444444444       30,000      30,000      180,000  200,000   90%     1  WARN
11111111-1111-4111-8111-111111111111        5,000       5,000        4,000  200,000    2%     1  -

threads=4  TRIGGER=1  WARN=1  ARCHIVE=1  ROLLOUT=0
```

## 2. JSON 输出

```bash
python scripts/measure_thread_context.py --json
```

输出供脚本 / 工具直接消费的 JSON 数组，字段：`thread_id`、`cum_input`、`last_turn_delta`、`last_usage`、`window`、`occupancy`、`turns`、`rollout_bytes`、`flags`。

## 3. 自动化检查（`--check`）

```bash
python scripts/measure_thread_context.py --check --sessions tests/fixtures/sessions
echo $?   # 3 = 存在 ARCHIVE 信号
```

退出码：`0` 正常 · `1` TRIGGER · `2` WARN · `3` ARCHIVE · `4` ROLLOUT（多信号取最高）。配合 cron 或 CI 可实现无人值守提醒。

## 4. 触发技能

在 Codex 中直接说：

```text
判断线程是否需要归档重开。先测量上下文用量，按阈值判定，不要自动归档。
```

技能会：测量 → 判定 → 只报告命中项，等待你确认后才进入 6 步归档周期（见 SKILL.md）。

## 5. 本地验证（开发 / 贡献者）

```bash
python scripts/validate_skill.py .                                   # 技能结构
python -m unittest discover -s tests -v                             # 单元测试
python scripts/measure_thread_context.py --check --sessions tests/fixtures/sessions
```