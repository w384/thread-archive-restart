# Contributing

Thanks for helping improve thread-archive-restart.

## Getting started

1. Fork the repository and clone it.
2. Install the skill into your Codex skills directory (see [README](README.md)).
3. Create a feature branch and make your changes.

## Development

The measurement script is Python 3.9+ and uses only the standard library.

Run the checks locally:

```bash
python scripts/validate_skill.py .                                    # skill structure
python -m unittest discover -s tests -v                              # unit tests
python scripts/measure_thread_context.py --check --sessions tests/fixtures/sessions  # smoke
```

## What to change

- `SKILL.md` — skill behavior, thresholds, and the archive-restart procedure.
- `scripts/measure_thread_context.py` — measurement logic and CLI.
- `README.md` / `README.zh-CN.md` / `docs/` — user-facing documentation; keep both languages in sync.
- `tests/` — add fixtures and cases for any new signal or option.

## Pull requests

- Keep commits small and descriptive.
- Update `CHANGELOG.md` under `[Unreleased]`.
- Ensure all checks above pass on Linux and Windows.
- Do not commit rollout files or other session data.

## License

By contributing, you agree that your contributions are licensed under the [MIT License](LICENSE).