"""Shared line selection for reviewed command-output reducers."""

from __future__ import annotations

import re

REDUCER_SCHEMA = "hydra.command-result.v1"
REDUCER_VERSION = "1"

SECRET_KEY_RE = re.compile(r"(password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|auth)", re.IGNORECASE)
ENV_ASSIGNMENT_RE = re.compile(r"(?P<prefix>(?:^|\s)[A-Za-z_][A-Za-z0-9_]*)(?P<eq>=)(?P<value>\"[^\"\r\n]*\"|'[^'\r\n]*'|[^\s]+)")
HEADER_SECRET_RE = re.compile(r"(?P<head>(?:authorization|proxy-authorization|x-api-key|api-key)\s*:\s*)(?P<value>\"[^\"\r\n]*\"|'[^'\r\n]*'|[^\r\n\"']+)", re.IGNORECASE)
QUERY_SECRET_RE = re.compile(r"(?P<key>[?&](?:token|api[_-]?key|access[_-]?token|secret|password)=)(?P<value>\"[^\"&\r\n]*\"|'[^'&\r\n]*'|[^&\s\"']+)", re.IGNORECASE)
FLAG_SECRET_RE = re.compile(r"(?P<flag>--(?:token|api-key|apikey|access-token|secret|password)(?:=|\s+))(?P<value>\"[^\"\r\n]*\"|'[^'\r\n]*'|[^\s\"']+)", re.IGNORECASE)
PROGRESS_RE = re.compile(r"^\s*(?:\d+%|\[\s*\d+%|[-\\|/]\s*$|[#=]{8,}|=>\s+\[[#= >.-]+\])")
TIMESTAMP_PREFIX_RE = re.compile(r"^\s*(?:\d{4}-\d{2}-\d{2}[T ][0-9:.]+(?:Z|[+-]\d{2}:?\d{2})?\s+){1,}")
REPEATED_WARNING_RE = re.compile(r"\bwarning\b", re.IGNORECASE)
PATH_OR_URL_RE = re.compile(r"(https?://\S+|(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+|[A-Za-z]:\\[^:\s]+)")
FILE_LINE_RE = re.compile(r"(^|[\s\"'([])([^:\s\"'()]+):(\d+)(?::(\d+))?")
STACK_RE = re.compile(r"^\s*(?:at\s+|File \"[^\"]+\", line \d+|Traceback\b|\w+(?:Error|Exception):)")
TEST_FAIL_RE = re.compile(r"(\bFAILED\b|\bFAIL\b|\bFAILURES\b|\bAssertionError\b|\bExpected\b|\bReceived\b)", re.IGNORECASE)
ERROR_RE = re.compile(r"(\berror\b|\bfailed\b|\bfailure\b|\bexception\b|\bfatal\b|\bpanic\b|\btimeout\b|\bdenied\b|\bcannot\b|\bnot found\b|\bCS\d{4}\b|\bTS\d{4}\b|\bNG\d{4}\b)", re.IGNORECASE)
STATS_RE = re.compile(r"(\b\d+\s+(?:error|errors|warning|warnings|failed|passed|skipped|total)\b|\bBuild (?:FAILED|succeeded)\b|\b\d+\s+files? changed\b|HTTP/[0-9.]+\s+\d{3})", re.IGNORECASE)
RESTORE_NOISE_RE = re.compile(r"^\s*(Determining projects to restore|Restored |Restore completed|All projects are up-to-date for restore|npm notice|added \d+ packages|up to date|Done in \d)", re.IGNORECASE)


def redact_obvious_secrets(text: str) -> str:
    def env_repl(match: re.Match[str]) -> str:
        key = match.group("prefix").strip()
        if SECRET_KEY_RE.search(key):
            return f"{match.group('prefix')}{match.group('eq')}<redacted>"
        return match.group(0)

    redacted = ENV_ASSIGNMENT_RE.sub(env_repl, text)
    redacted = HEADER_SECRET_RE.sub(lambda match: f"{match.group('head')}<redacted>", redacted)
    redacted = QUERY_SECRET_RE.sub(lambda match: f"{match.group('key')}<redacted>", redacted)
    return FLAG_SECRET_RE.sub(lambda match: f"{match.group('flag')}<redacted>", redacted)


def reduction_fields(command_output, family: str, reducer_name: str, max_lines: int) -> dict:
    redacted_output = redact_obvious_secrets(command_output.output)
    important = tuple(important_lines(redacted_output, family, max_lines))
    compact = compact_summary(family, command_output.exit_code, redacted_output, important)
    omitted_lines = omitted_line_count(important, command_output.line_count)
    return {
        "schema": REDUCER_SCHEMA,
        "provider": command_output.provider or "manual",
        "tool_name": command_output.tool_name,
        "command": redact_obvious_secrets(command_output.command),
        "cwd": command_output.cwd,
        "exit_code": command_output.exit_code,
        "family": family,
        "reducer_name": reducer_name,
        "reducer_version": REDUCER_VERSION,
        "compact_summary": compact,
        "important_lines": important,
        "omitted_lines": omitted_lines,
        "omitted_chars": max(0, len(redacted_output) - len("\n".join(important))),
        "input_line_count": command_output.line_count,
        "input_char_count": command_output.char_count,
        "session_id": command_output.session_id,
        "key": command_output.key,
    }


def important_lines(text: str, family: str, max_lines: int) -> list[str]:
    lines = text.splitlines()
    if not lines:
        return []
    indexes = candidate_indexes(lines, family, max_lines)
    result: list[str] = []
    previous = -1
    for index in indexes:
        if previous >= 0 and index != previous + 1:
            result.append("...")
        result.append(f"L{index + 1}: {lines[index]}")
        previous = index
    omitted = len(lines) - sum(1 for line in result if line != "...")
    if omitted > 0:
        result.append(f"... omitted {omitted} lines")
    return result


def candidate_indexes(lines: list[str], family: str, max_lines: int) -> list[int]:
    selected: list[int] = []
    seen_warnings: set[str] = set()

    def add(index: int, neighbors: int = 0) -> None:
        for nearby in range(max(0, index - neighbors), min(len(lines), index + neighbors + 1)):
            if len(lines[nearby]) <= 2000 and not line_is_noise(lines[nearby], family) and nearby not in selected:
                selected.append(nearby)

    for index, line in enumerate(lines):
        if line_is_noise(line, family):
            continue
        normalized = normalized_repetition_key(line)
        source_candidate = TIMESTAMP_PREFIX_RE.sub("", line)
        if REPEATED_WARNING_RE.search(line) and normalized in seen_warnings:
            continue
        if REPEATED_WARNING_RE.search(line):
            seen_warnings.add(normalized)
        if ERROR_RE.search(line) or STACK_RE.search(line) or FILE_LINE_RE.search(source_candidate) or TEST_FAIL_RE.search(line):
            add(index, 2 if family in {"dotnet-build", "dotnet-test", "yarn-test", "npm-test"} else 1)
        elif family == "git-diff" and (line.startswith(("diff --git ", "index ", "--- ", "+++ ", "@@")) or line.startswith(("+", "-"))):
            add(index)
        elif family == "git-status" or (family in {"curl-request", "ripgrep-search"} and (PATH_OR_URL_RE.search(line) or STATS_RE.search(line))) or STATS_RE.search(line):
            add(index)
    return sorted(selected)[:max_lines]


def fallback_indexes(lines: list[str], max_lines: int) -> list[int]:
    head_count = min(len(lines), max_lines // 2)
    tail_count = min(max(0, len(lines) - head_count), max_lines - head_count)
    selected = set(range(head_count))
    if tail_count:
        selected.update(range(len(lines) - tail_count, len(lines)))
    return sorted(selected)


def line_is_noise(line: str, family: str) -> bool:
    stripped = line.strip()
    if not stripped or PROGRESS_RE.search(stripped):
        return True
    families = {"dotnet-build", "dotnet-restore", "yarn-install", "yarn-build", "yarn-check-types", "npm-install", "npm-build"}
    return family in families and RESTORE_NOISE_RE.search(stripped) is not None


def normalized_repetition_key(line: str) -> str:
    line = TIMESTAMP_PREFIX_RE.sub("", line.strip())
    line = re.sub(r"\b\d{4}-\d{2}-\d{2}[T ][0-9:.]+(?:Z|[+-]\d{2}:?\d{2})?\b", "<time>", line)
    return re.sub(r"\b\d+\b", "<n>", line)

def omitted_line_count(important: tuple[str, ...], total_lines: int) -> int:
    return max(0, total_lines - sum(1 for line in important if line.startswith("L")))


def compact_summary(family: str, exit_code: int | None, text: str, important: tuple[str, ...]) -> str:
    status = "failed" if exit_code is not None and exit_code != 0 else "succeeded"
    status = "completed" if exit_code is None else status
    lines = text.splitlines()
    stats = [line.strip() for line in lines if STATS_RE.search(line) and not line_is_noise(line, family)]
    error = next((line.strip() for line in lines if ERROR_RE.search(line) and not line_is_noise(line, family)), "")
    detail = stats[-1] if stats else error
    base = f"{family} {status}"
    if exit_code is not None:
        base += f" with exit code {exit_code}"
    if detail:
        base += f": {detail}"
    return f"{base}; kept {sum(1 for line in important if line.startswith('L'))} important lines"
