#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate a Codex skill folder (CI-friendly, stdlib only).

Checks (mirrors the spirit of the official quick_validate):
  1. SKILL.md exists at the folder root.
  2. YAML frontmatter is delimited by leading ``---`` fences.
  3. ``name`` equals the folder name (lowercase letters, digits, hyphens).
  4. ``description`` is present and non-empty.
  5. No extra top-level fields beyond name/description.
  6. Neither field contains angle brackets.

Usage:
  python scripts/validate_skill.py <skill-folder>

Exit 0 on success, 1 on failure.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


def parse_frontmatter(text: str):
    """Parse simple single-line key: value frontmatter between leading --- fences."""
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end < 0:
        return None
    block = text[3:end]
    fields = {}
    for line in block.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if not match:
            return None
        fields[match.group(1)] = match.group(2).strip().strip('"').strip("'")
    return fields


def validate(folder: Path) -> list[str]:
    errors = []
    skill_md = folder / "SKILL.md"
    if not skill_md.is_file():
        errors.append(f"missing SKILL.md in {folder}")
        return errors
    frontmatter = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
    if frontmatter is None:
        errors.append("SKILL.md frontmatter is missing or malformed")
        return errors
    name = frontmatter.get("name")
    if not name:
        errors.append("frontmatter `name` is required")
    elif folder.name != name:
        errors.append(f"folder name {folder.name!r} != frontmatter name {name!r}")
    description = frontmatter.get("description")
    if not description:
        errors.append("frontmatter `description` is required")
    extra = set(frontmatter) - {"name", "description"}
    if extra:
        errors.append(f"unexpected frontmatter fields: {sorted(extra)}")
    for field in ("name", "description"):
        value = frontmatter.get(field) or ""
        if "<" in value or ">" in value:
            errors.append(f"frontmatter `{field}` contains angle brackets")
    return errors


def main(argv=None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if len(argv) != 1:
        print(__doc__)
        return 2
    errors = validate(Path(argv[0]))
    if errors:
        print("INVALID:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())