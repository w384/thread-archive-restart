# Security

## Reporting a vulnerability

Please do not open a public issue for security problems. Once the repository is on GitHub, report privately via the repository's Security tab; until then, contact the maintainer directly.

## Scope

- The measurement script reads local session rollout files and prints aggregate numbers. It makes no network calls and uploads nothing.
- Rollout files can contain conversation content. They are ignored by `.gitignore` and must never be committed, copied to shared locations, or pasted into issues.
- Thresholds are advisory: the skill never archives, deletes, or moves anything without explicit user confirmation.