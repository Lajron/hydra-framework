"""Log excerpt selection and summarization.

Moved unchanged from `scripts/hydra.py`'s `selected_log_indexes`/
`summarize_log_text`.
"""

from __future__ import annotations

import re

LOG_INTERESTING_RE = re.compile(
    r"(error|failed|failure|exception|traceback|assert|fatal|panic|timeout|denied|cannot|not found|"
    r"\bCS\d{4}\b|\bTS\d{4}\b|\bNG\d{4}\b|^\s*at\s+|\.py\", line \d+|:\d+:\d+)",
    re.IGNORECASE,
)
LOG_NOISE_RE = re.compile(
    r"^\s*(\[\s*\d+%|\d+%|download(ed|ing)|restore completed|determining projects to restore|"
    r"npm notice|added \d+ packages|up to date)",
    re.IGNORECASE,
)

LOG_CONTEXT_BEFORE_LINES = 2
LOG_CONTEXT_AFTER_LINES = 2


def selected_log_indexes(lines: list[str], max_lines: int) -> list[int]:
    interesting: set[int] = set()
    for index, line in enumerate(lines):
        if LOG_NOISE_RE.search(line):
            continue
        if LOG_INTERESTING_RE.search(line):
            start = max(0, index - LOG_CONTEXT_BEFORE_LINES)
            end = min(len(lines), index + LOG_CONTEXT_AFTER_LINES + 1)
            for neighbor in range(start, end):
                if not LOG_NOISE_RE.search(lines[neighbor]):
                    interesting.add(neighbor)

    if not interesting:
        head_count = min(len(lines), max_lines // 2)
        tail_count = min(max(0, len(lines) - head_count), max_lines - head_count)
        interesting.update(range(head_count))
        if tail_count:
            interesting.update(range(len(lines) - tail_count, len(lines)))

    return sorted(interesting)[:max_lines]


def summarize_log_text(text: str, max_lines: int) -> list[str]:
    lines = text.splitlines()
    if not lines:
        return []
    selected = selected_log_indexes(lines, max_lines)
    summary: list[str] = []
    previous = -1
    for index in selected:
        if previous >= 0 and index != previous + 1:
            summary.append("...")
        summary.append(f"L{index + 1}: {lines[index]}")
        previous = index
    omitted = len(lines) - sum(1 for line in summary if line != "...")
    if omitted > 0:
        summary.append(f"... omitted {omitted} lines")
    return summary
