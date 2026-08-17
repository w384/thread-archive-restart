# Thread Archive & Restart

Decide when a Codex thread has outgrown its context window, and run a handoff-first archive-and-restart cycle — with data, not guesswork.

[中文 README](README.zh-CN.md)

## Why does context matter for long-running threads?

Every long agent conversation accumulates input tokens until the context window is nearly full: replies slow down, early decisions get forgotten, and behavior becomes unstable. The common fixes — "just continue", manual summarization, or in-place compaction — either ignore the problem or risk losing decisions and verification state.

Thread Archive & Restart answers the earlier question: **is this thread too big? Should we archive it and start a fresh one?** It measures real usage from Codex session rollouts, applies explicit thresholds, and then runs a *handoff-first* cycle so nothing is lost:

```text
Measure all threads
   → threshold hit? (notify, wait for confirmation)
   → update handoff doc
   → pre-archive verification
   → archive old thread
   → rebuild worktree
   → open new thread + restate responsibilities
   → mark handoff status
```

## Features

- Measures every thread's cumulative input, latest-turn delta, last-call input, window occupancy, and rollout file size directly from `$CODEX_HOME/sessions`.
- Explicit, documented thresholds: single-turn spike, cumulative input, rollout size, occupancy warning.
- **Semi-automatic by design**: detection only notifies; archiving always waits for user confirmation.
- `--check` mode with exit codes for cron / CI / pre-hook automation.
- Zero runtime dependencies (Python standard library only), runs on any OS where Codex runs.

## Thresholds

| Signal | Threshold | Action |
|---|---|---|
| Latest-turn input delta (TRIGGER) | ≥ 200,000 tokens | Archive & restart after the current task |
| Cumulative input incl. replays (ARCHIVE) | ≥ 10,000,000 tokens | Thread-level archive |
| Rollout file size (ROLLOUT) | > 5 MB | Thread-level archive |
| Window occupancy (WARN) | ≥ 80% | Warn only, not enforced |

Any signal triggers a notification; the actual archive is executed only after you confirm.

## Installation

### As a Codex skill (recommended)

```bash
git clone https://github.com/w384/thread-archive-restart "${CODEX_HOME:-$HOME/.codex}/skills/thread-archive-restart"
```

Windows PowerShell:

```powershell
$codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME '.codex' }
git clone https://github.com/w384/thread-archive-restart (Join-Path $codexHome 'skills\thread-archive-restart')
```

Restart Codex — SKILL.md is auto-discovered.

### As a standalone CLI

The measurement script needs only the standard library:

```bash
python scripts/measure_thread_context.py            # table
python scripts/measure_thread_context.py --json     # machine-readable
python scripts/measure_thread_context.py --check    # exit codes for automation
```

## Usage

Ask Codex to check the current thread:

```text
判断线程是否需要归档重开。先测量上下文用量，按阈值判定，不要自动归档。
```

Or, in English:

```text
Use thread-archive-restart. Measure all threads, decide against the thresholds, and report — do not archive anything without my confirmation.
```

### CLI reference

| Option | Default | Description |
|---|---|---|
| `--days N` | all | Only consider rollout files modified within the last N days |
| `--json` | off | Emit the report as JSON |
| `--check` | off | Exit non-zero when a signal is raised |
| `--sessions DIR` | `$CODEX_HOME/sessions` | Sessions directory to scan |
| `--threshold-turn N` | 200000 | TRIGGER: latest-turn delta threshold |
| `--threshold-cum N` | 10000000 | ARCHIVE: cumulative input threshold |
| `--warn-occupancy F` | 0.8 | WARN: window occupancy threshold (0..1) |
| `--rollout-size-bytes N` | 5242880 | ROLLOUT: rollout file size threshold |
| `--version` | — | Print version |

### Automation with `--check`

Exit codes: `0` ok · `1` TRIGGER · `2` WARN · `3` ARCHIVE · `4` ROLLOUT (highest severity wins).

```bash
python scripts/measure_thread_context.py --check --json
code=$?
if [ "$code" -ne 0 ]; then
  echo "context monitor: a thread needs attention (exit $code)"
fi
```

## Project layout

```text
thread-archive-restart/
├── SKILL.md                       # Codex skill entry point (thresholds + 6-step cycle)
├── scripts/
│   ├── measure_thread_context.py  # measurement CLI (stdlib only)
│   └── validate_skill.py          # CI-friendly skill structure validator
├── tests/                         # unittest suite + synthetic session fixtures
├── docs/                          # design rationale & demo walkthrough
└── .github/workflows/ci.yml       # CI: validate + test + smoke on every push/PR
```

## Measurement & privacy

The script reads only local rollout files under your sessions directory and prints aggregate numbers. It makes no network calls and uploads nothing. Rollout files may contain conversation content — never commit them to a repository (see `.gitignore`).

## Comparison with alternatives

| Approach | Primary question | How Thread Archive & Restart differs |
|---|---|---|
| Memory systems | What should be saved and retrieved? | Decides *when a thread should end* and how to hand off, not what to remember. |
| Prompt/context compression | How to fit more into the same window? | Restarts with a fresh window instead of compressing the existing one. |
| Manual re-summarization | How do I summarize this myself? | Provides measurable thresholds and a repeatable handoff-first procedure. |

These complement each other: compress or govern context while a thread is healthy; archive and restart when it is not.

## Roadmap

- **v0.1** — Measurement CLI (table / JSON / check), thresholds, handoff-first archive cycle, tests and CI, bilingual docs.
- **Next** — Optional `--summary` output that drafts the handoff section from measured thread state; release automation.
- **Later** — Plugins for other agent runtimes, and a gallery of archive-restart case studies.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Reports and feature requests are welcome via GitHub Issues; security concerns go to [SECURITY.md](SECURITY.md).

## License

MIT. See [LICENSE](LICENSE).

## Repository metadata

Suggested GitHub description:

> Decide when a Codex thread has outgrown its context window and run a handoff-first archive-and-restart cycle with measurable thresholds.

Suggested topics:

codex · openai-codex · skill · ai-agent · context-engineering · context-management · thread-management · agent-lifecycle · developer-tools

See [CHANGELOG.md](CHANGELOG.md) for the v0.1.0 release notes.