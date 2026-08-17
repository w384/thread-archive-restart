# Changelog

All notable changes to this project are documented in this file.

The format follows the spirit of [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and version numbers follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

- No unreleased changes yet.

## [0.1.0] - 2026-08-17

### Added

- Initial Thread Archive & Restart Codex Skill: thresholds (TRIGGER / ARCHIVE / ROLLOUT / WARN) and the handoff-first archive-and-restart cycle.
- Measurement CLI `scripts/measure_thread_context.py`: table / JSON / `--check` output, tunable thresholds, `--sessions` override, `--version`.
- `scripts/validate_skill.py`: CI-friendly, dependency-free skill structure validator.
- Unit test suite with synthetic session rollout fixtures (stdlib unittest).
- GitHub Actions CI: structure validation, tests, and `--check` smoke tests on Linux and Windows.
- Bilingual README (English / 中文), design notes, demo walkthrough, contributing and security docs.

[Unreleased]: https://github.com/w384/thread-archive-restart/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/w384/thread-archive-restart/releases/tag/v0.1.0