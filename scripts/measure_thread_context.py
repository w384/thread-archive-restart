#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Measure per-thread Codex context usage from session rollout files.

Reads $CODEX_HOME/sessions/**/rollout-*.jsonl (override with --sessions DIR)
token_count events and reports per thread: cumulative input, latest-turn
input delta, last-call input, window occupancy, and signal flags.

Signals (any match makes the thread a restart candidate):

  TRIGGER  - latest-turn input delta    >= threshold_turn     (default 200,000)
  ARCHIVE  - cumulative input (replays) >= threshold_cum      (default 10,000,000)
  ROLLOUT  - rollout file size          >= threshold_rollout  (default 5 MB)
  WARN     - window occupancy           >= warn_occupancy     (default 0.80)

Exit codes (with --check; highest severity wins):

  0 = ok, 1 = TRIGGER, 2 = WARN, 3 = ARCHIVE, 4 = ROLLOUT

Usage:
  python measure_thread_context.py [--days N] [--json] [--check]
                                   [--sessions DIR] [--threshold-* ...]
"""
from __future__ import annotations

import argparse
import datetime
import glob
import json
import os
import re
import sys
from typing import Any, Optional

__version__ = "0.1.0"

DEFAULT_CODEX_HOME = os.path.expanduser("~/.codex")
DEFAULT_SESSIONS = os.path.join(
    os.environ.get("CODEX_HOME") or DEFAULT_CODEX_HOME, "sessions"
)

THREAD_RE = re.compile(
    r"-([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\.jsonl$"
)
TURN_START_TYPES = {"user_message", "task_started"}

DEFAULT_TURN_INPUT = 200_000
DEFAULT_CUM_INPUT = 10_000_000
DEFAULT_ROLLOUT_BYTES = 5 * 1024 * 1024
DEFAULT_WARN_OCCUPANCY = 0.80

EXIT_OK = 0
SEVERITY = {"TRIGGER": 1, "WARN": 2, "ARCHIVE": 3, "ROLLOUT": 4}


def rollout_files(sessions_dir: str, days: Optional[int]):
    cutoff_ts = None
    if days:
        cutoff_ts = (datetime.datetime.now() - datetime.timedelta(days=days)).timestamp()
    for path in glob.glob(os.path.join(sessions_dir, "**", "rollout-*.jsonl"), recursive=True):
        if cutoff_ts is not None and os.path.getmtime(path) < cutoff_ts:
            continue
        yield path


def thread_id_of(path: str) -> Optional[str]:
    match = THREAD_RE.search(os.path.basename(path))
    return match.group(1) if match else None


def load_events(path: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                events.append(json.loads(raw))
            except (ValueError, TypeError):
                continue
    return events


def analyze_thread(
    events: list[dict[str, Any]],
    *,
    threshold_turn: int,
    threshold_cum: int,
    warn_occupancy: float,
) -> Optional[dict[str, Any]]:
    """Reduce a thread's rollout events to a metrics row (or None if unusable)."""
    events = sorted(events, key=lambda o: o.get("timestamp") or "")
    last_total = None
    last_usage = None
    window = None
    turn_base = 0
    turn_starts = 0
    for event in events:
        if event.get("type") != "event_msg":
            continue
        payload = event.get("payload")
        if not isinstance(payload, dict):
            continue
        ptype = payload.get("type")
        if ptype in TURN_START_TYPES:
            turn_base = last_total if last_total is not None else 0
            turn_starts += 1
        elif ptype == "token_count":
            info = payload.get("info") or {}
            total = info.get("total_token_usage") or {}
            last = info.get("last_token_usage") or {}
            if isinstance(total.get("input_tokens"), (int, float)):
                last_total = int(total["input_tokens"])
            if isinstance(last.get("input_tokens"), (int, float)):
                last_usage = int(last["input_tokens"])
            if isinstance(info.get("model_context_window"), (int, float)):
                window = int(info["model_context_window"])
    if last_total is None:
        return None
    turn_delta = max(0, last_total - turn_base)
    occupancy = (last_usage / window) if (last_usage is not None and window) else None
    flags: list[str] = []
    if turn_delta >= threshold_turn:
        flags.append("TRIGGER")
    if last_total >= threshold_cum:
        flags.append("ARCHIVE")
    if occupancy is not None and occupancy >= warn_occupancy:
        flags.append("WARN")
    return {
        "thread_id": None,  # filled by scan()
        "cum_input": last_total,
        "last_turn_delta": turn_delta,
        "last_usage": last_usage,
        "window": window,
        "occupancy": round(occupancy, 4) if occupancy is not None else None,
        "turns": turn_starts,
        "flags": flags,
    }


def scan(
    sessions_dir: str,
    *,
    days: Optional[int] = None,
    threshold_turn: int = DEFAULT_TURN_INPUT,
    threshold_cum: int = DEFAULT_CUM_INPUT,
    warn_occupancy: float = DEFAULT_WARN_OCCUPANCY,
    rollout_size_bytes: int = DEFAULT_ROLLOUT_BYTES,
) -> list[dict[str, Any]]:
    per_thread: dict[str, list[dict[str, Any]]] = {}
    sizes: dict[str, int] = {}
    for path in rollout_files(sessions_dir, days):
        thread_id = thread_id_of(path)
        if not thread_id:
            continue
        per_thread.setdefault(thread_id, []).extend(load_events(path))
        sizes[thread_id] = max(sizes.get(thread_id, 0), os.path.getsize(path))

    report = []
    for thread_id, events in per_thread.items():
        row = analyze_thread(
            events,
            threshold_turn=threshold_turn,
            threshold_cum=threshold_cum,
            warn_occupancy=warn_occupancy,
        )
        if row is None:
            continue
        row["thread_id"] = thread_id
        row["rollout_bytes"] = sizes.get(thread_id, 0)
        if rollout_size_bytes and row["rollout_bytes"] >= rollout_size_bytes:
            row["flags"].append("ROLLOUT")
        report.append(row)
    report.sort(key=lambda r: -(r["cum_input"] or 0))
    return report


def render_text(report: list[dict[str, Any]]) -> str:
    lines = [
        f"{'thread_id':<38}{'cum_input':>12}{'turn_delta':>11}{'last_usage':>11}"
        f"{'window':>8}{'occ':>6}{'turns':>4}  flags"
    ]
    for row in report:
        occ = f"{row['occupancy'] * 100:.0f}%" if row["occupancy"] is not None else "-"
        flags = ",".join(row["flags"]) if row["flags"] else "-"
        lines.append(
            f"{row['thread_id']:<38}{row['cum_input']:>12,}{row['last_turn_delta']:>11,}"
            f"{(row['last_usage'] or 0):>11,}{(row['window'] or 0):>8,}{occ:>6}"
            f"{row['turns']:>4}  {flags}"
        )
    lines.append(
        f"\nthreads={len(report)}  "
        f"TRIGGER={sum(1 for r in report if 'TRIGGER' in r['flags'])}  "
        f"WARN={sum(1 for r in report if 'WARN' in r['flags'])}  "
        f"ARCHIVE={sum(1 for r in report if 'ARCHIVE' in r['flags'])}  "
        f"ROLLOUT={sum(1 for r in report if 'ROLLOUT' in r['flags'])}"
    )
    return "\n".join(lines)


def render_json(report: list[dict[str, Any]]) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2)


def exit_code_for(report: list[dict[str, Any]]) -> int:
    codes = [SEVERITY[flag] for row in report for flag in row.get("flags", [])]
    return max(codes, default=EXIT_OK)


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="measure_thread_context",
        description="Measure per-thread Codex context usage from session rollout files.",
    )
    parser.add_argument(
        "--days", type=int, default=None,
        help="only consider rollout files modified within the last N days",
    )
    parser.add_argument("--json", action="store_true", help="emit the report as JSON")
    parser.add_argument(
        "--check", action="store_true",
        help="exit non-zero when a signal is raised (see exit codes)",
    )
    parser.add_argument(
        "--sessions", default=DEFAULT_SESSIONS,
        help="sessions directory (default: $CODEX_HOME/sessions)",
    )
    parser.add_argument(
        "--threshold-turn", type=int, default=DEFAULT_TURN_INPUT,
        help="TRIGGER: latest-turn input delta threshold (default 200000)",
    )
    parser.add_argument(
        "--threshold-cum", type=int, default=DEFAULT_CUM_INPUT,
        help="ARCHIVE: cumulative input threshold (default 10000000)",
    )
    parser.add_argument(
        "--warn-occupancy", type=float, default=DEFAULT_WARN_OCCUPANCY,
        help="WARN: window occupancy threshold in 0..1 (default 0.8)",
    )
    parser.add_argument(
        "--rollout-size-bytes", type=int, default=DEFAULT_ROLLOUT_BYTES,
        help="ROLLOUT: rollout file size threshold in bytes (default 5242880)",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    report = scan(
        args.sessions,
        days=args.days,
        threshold_turn=args.threshold_turn,
        threshold_cum=args.threshold_cum,
        warn_occupancy=args.warn_occupancy,
        rollout_size_bytes=args.rollout_size_bytes,
    )
    print(render_json(report) if args.json else render_text(report))
    return exit_code_for(report) if args.check else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())