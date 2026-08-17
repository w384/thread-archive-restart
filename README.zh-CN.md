# Thread Archive & Restart（线程归档重开）

用数据判断 Codex 线程何时超出上下文窗口，并执行"交接包优先"的归档重开周期——不靠猜。

[English README](README.md)

## 长任务为什么需要关注上下文？

长任务 agent 会话会不断累积 input tokens，直到上下文窗口接近满载：回复变慢、早期决策被遗忘、行为变得不稳定。常见的做法——"硬继续"、手动总结、原地压缩——要么忽略问题，要么冒着丢失决策和验证状态的风险。

Thread Archive & Restart 回答更早的问题：**这个线程是不是太大了？该归档并重开一个吗？** 它从 Codex 会话 rollout 中测量真实用量，按明确的阈值判定，然后执行"交接包优先"的周期，确保不丢任何东西：

```text
测量所有线程
   → 阈值命中？（通知，等待确认）
   → 更新交接包
   → 归档前核验
   → 归档旧线程
   → 重建工作区
   → 开新线程 + 复述职责
   → 标记交接状态
```

## 特性

- 直接从 `$CODEX_HOME/sessions` 测量每个线程的累计 input、最近一轮增量、最近一次调用 input、窗口占用与 rollout 文件大小。
- 明确、可文档化的阈值：单轮激增、累计 input、rollout 体积、窗口占用预警。
- **默认半自动**：检测只通知；归档执行前必须由用户确认。
- `--check` 模式提供退出码，便于 cron / CI / 钩子自动化。
- 零运行时依赖（仅 Python 标准库），任何能跑 Codex 的系统都能用。

## 阈值

| 信号 | 阈值 | 动作 |
|---|---|---|
| 最近一轮 input 增量（TRIGGER） | ≥ 200,000 tokens | 当前任务完成后归档重开 |
| 会话累计 input 含重放（ARCHIVE） | ≥ 10,000,000 tokens | 线程级归档 |
| rollout 文件超限（ROLLOUT） | > 5 MB | 线程级归档 |
| 窗口占用（WARN） | ≥ 80% | 仅预警，不强制 |

任一信号命中都只触发通知；真正归档需你确认后才会执行。

## 安装

### 作为 Codex 技能（推荐）

```bash
git clone https://github.com/w384/thread-archive-restart "${CODEX_HOME:-$HOME/.codex}/skills/thread-archive-restart"
```

Windows PowerShell：

```powershell
$codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME '.codex' }
git clone https://github.com/w384/thread-archive-restart (Join-Path $codexHome 'skills\thread-archive-restart')
```

重启 Codex 后自动发现 SKILL.md。

### 作为独立 CLI

测量脚本只依赖标准库：

```bash
python scripts/measure_thread_context.py            # 表格
python scripts/measure_thread_context.py --json     # 机器可读
python scripts/measure_thread_context.py --check    # 供自动化使用的退出码
```

## 使用

让 Codex 检查当前线程：

```text
判断线程是否需要归档重开。先测量上下文用量，按阈值判定，不要自动归档。
```

### CLI 参考

| 选项 | 默认值 | 说明 |
|---|---|---|
| `--days N` | 全部 | 只考虑最近 N 天内修改的 rollout 文件 |
| `--json` | 关 | 以 JSON 输出报告 |
| `--check` | 关 | 命中信号时以非零退出 |
| `--sessions DIR` | `$CODEX_HOME/sessions` | 要扫描的会话目录 |
| `--threshold-turn N` | 200000 | TRIGGER：最近一轮增量阈值 |
| `--threshold-cum N` | 10000000 | ARCHIVE：累计 input 阈值 |
| `--warn-occupancy F` | 0.8 | WARN：窗口占用阈值（0..1） |
| `--rollout-size-bytes N` | 5242880 | ROLLOUT：rollout 文件大小阈值 |
| `--version` | — | 打印版本 |

### 用 `--check` 做自动化

退出码：`0` 正常 · `1` TRIGGER · `2` WARN · `3` ARCHIVE · `4` ROLLOUT（多信号取最高）。

```bash
python scripts/measure_thread_context.py --check --json
code=$?
if [ "$code" -ne 0 ]; then
  echo "context monitor: a thread needs attention (exit $code)"
fi
```

## 目录结构

```text
thread-archive-restart/
├── SKILL.md                       # 技能入口（阈值 + 6 步归档周期）
├── scripts/
│   ├── measure_thread_context.py  # 测量 CLI（仅标准库）
│   └── validate_skill.py          # 面向 CI 的技能结构校验器
├── tests/                         # unittest 套件 + 合成会话 fixture
├── docs/                          # 设计说明与演示
└── .github/workflows/ci.yml       # CI：每次 push/PR 校验 + 测试 + 冒烟
```

## 测量与隐私

脚本只读取你本地 sessions 目录下的 rollout 文件并打印汇总数字，不发网络请求、不上传任何内容。rollout 文件可能包含对话内容——绝不要提交到仓库（参见 `.gitignore`）。

## 与同类方案对比

| 方案 | 核心问题 | 本技能的不同 |
|---|---|---|
| 记忆系统 | 该保存 / 检索什么？ | 决定*线程何时该结束*以及如何交接，而不是记住什么。 |
| 提示词 / 上下文压缩 | 怎么在同一窗口装更多？ | 用全新窗口重启，而不是压缩现有窗口。 |
| 手动重述总结 | 我自己怎么总结？ | 提供可测阈值和可复用的交接包优先流程。 |

二者互补：线程健康时压缩 / 治理上下文；不健康时归档重开。

## 路线图

- **v0.1** — 测量 CLI（表格 / JSON / check）、阈值、交接包优先归档周期、测试与 CI、双语文档。
- **下一步** — 可选 `--summary` 输出（根据测量的线程状态草拟交接包章节）；发布自动化。
- **以后** — 其他 agent 运行时的插件，以及归档重开案例集。

## 贡献

见 [CONTRIBUTING.md](CONTRIBUTING.md)。问题与功能建议欢迎走 GitHub Issues；安全相关问题见 [SECURITY.md](SECURITY.md)。

## 许可证

MIT。见 [LICENSE](LICENSE)。

## 仓库元数据

建议的 GitHub 描述：

> 用可测阈值判断 Codex 线程何时超出上下文窗口，并执行交接包优先的归档重开周期。

建议的 topics：

codex · openai-codex · skill · ai-agent · context-engineering · context-management · thread-management · agent-lifecycle · developer-tools

v0.1.0 发布说明见 [CHANGELOG.md](CHANGELOG.md)。