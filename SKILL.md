---
name: thread-archive-restart
description: 判断 Codex 线程是否需要归档重开，并执行"交接包优先"的归档重开全流程。当线程上下文已膨胀（会话累计 input 达 1000 万 tokens、最近一轮 input 增量达 20 万 tokens、或 rollout 文件超 5MB）、长任务已完成想换新线程继续、或用户要求归档 / 重开 / 重建 / 交接一个对话时使用。覆盖从 rollout 会话文件测量各线程 input、按阈值判定、到 更新交接包 → 归档前核验 → 归档 → 重建工作区 → 开新线程 → 复述确认 的完整周期。
---

# Thread Archive & Restart（线程归档重开）

## Decide（判定）

测量所有线程的上下文用量：

```bash
python scripts/measure_thread_context.py [--days N] [--json] [--check]
```

阈值（任一命中 → 当前任务完成后归档，不打断在途任务）：

| 信号 | 阈值 | 动作 |
| --- | --- | --- |
| 最近一轮 input 增量（TRIGGER） | ≥ 200,000 tokens | 当前任务完成后归档重开 |
| 会话累计 input 含重放（ARCHIVE） | ≥ 10,000,000 tokens | 线程级归档 |
| rollout 文件超限（ROLLOUT） | > 5 MB | 线程级归档 |
| 窗口占用（WARN） | ≥ 80% | 预警，不强制 |

- 半自动：检测到阈值只通知用户；归档执行前必须获得用户确认，不自动归档。
- `--check` 供自动化使用：退出码 0=无信号、1=TRIGGER、2=WARN、3=ARCHIVE、4=ROLLOUT（多信号取最高）。
- 阈值可调：`--threshold-turn` / `--threshold-cum` / `--warn-occupancy` / `--rollout-size-bytes`；`--sessions DIR` 指定会话目录（测试 / CI 用）。
- 测量口径：累计 input 取 `total_token_usage.input_tokens` 最新值；最近一轮增量按 `user_message`/`task_started` 轮次边界计算。

## Execute（交接包优先，按序执行）

1. **更新交接包**：把线程当前状态写入共享交接包的对应章节（状态基线 / git 基线 / 剩余待办 / 关键决策 / 风险）。核对引用的文件路径真实存在；归档前不提交、不推送、不发布。
2. **归档前核验**：让旧线程只回复 ①工作区完整路径 ②其维护的文件清单 + 落盘状态 ③在途任务卡点 ④确认交接包章节完整、无未落盘口头决策。
3. **归档旧线程**：用户在 Codex 客户端归档（旧线程不可用）。
4. **重建工作区**：在标准位置重建 worktree（`git worktree add`），确认 git 注册与反向指针正常。
5. **开新线程**：首条消息 = 只读 项目权威契约 + 交接包中该线程章节；复述职责与红线；等用户确认后再接派单。
6. **更新交接包状态**：标记「已归档重开」。

## Context governance（与 context-governance 技能协同）

- 归档是"把细节移出常驻层"，不是删除：交接包 = 归档式摘要，保留逻辑脉络（git log 式逐轮记录）。
- 保留优先级：架构决策与关键约束不得摘要；已修改文件与变更记录完整保留；验证状态（pass/fail）必留；未解决 TODO 与回滚笔记必留；工具输出可删。
- 项目特定细节以该项目 `docs/agent/thread-archive-sop.md` 为准；本技能是通用方法。

## CLI 参考

完整 CLI 参数、退出码与自动化示例见仓库 README.md（本技能开源仓库根目录）。