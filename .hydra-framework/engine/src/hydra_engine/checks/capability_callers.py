"""Capability caller validation.

Two kinds of evidence are checked here:

- `command_*` implementations must be reachable from argparse registration,
  including this repo's common `set_defaults(func=_dispatch_x)` wrapper shape.
- Cross-surface mechanisms that cannot be derived from argparse must keep a
  small snippet-validated evidence file under `validation/`.
"""

from __future__ import annotations

import ast
from pathlib import Path

from hydra_engine.documents.tokens import display_path, read_text
from hydra_engine.finding import Finding

SCHEMA = "hydra-framework.capability-callers.v1"
VALID_CLASSIFICATIONS = frozenset({"automatic", "manual", "intentionally-disabled"})


def implementation_source_files(hydra: Path) -> list[Path]:
    files: list[Path] = []
    shim = hydra / "scripts" / "hydra.py"
    if shim.exists():
        files.append(shim)
    package_root = hydra / "engine" / "src" / "hydra_engine"
    if package_root.is_dir():
        files.extend(sorted(path for path in package_root.rglob("*.py") if "__pycache__" not in path.parts))
    return files


def _call_names(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        if isinstance(child.func, ast.Name):
            names.add(child.func.id)
        elif isinstance(child.func, ast.Attribute):
            names.add(child.func.attr)
    return names


def _registered_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute) or node.func.attr != "set_defaults":
            continue
        for keyword in node.keywords:
            if keyword.arg != "func":
                continue
            value = keyword.value
            if isinstance(value, ast.Name):
                names.add(value.id)
            elif isinstance(value, ast.Lambda):
                names.update(_call_names(value.body))
            elif isinstance(value, ast.Attribute):
                names.add(value.attr)
    return names


def _discover_commands(source_files: list[Path]) -> tuple[dict[str, Path], set[str], dict[str, set[str]]]:
    command_defs: dict[str, Path] = {}
    registered: set[str] = set()
    calls_by_function: dict[str, set[str]] = {}
    for path in source_files:
        try:
            tree = ast.parse(read_text(path), filename=str(path))
        except SyntaxError:
            continue
        registered.update(_registered_names(tree))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("command_"):
                    command_defs.setdefault(node.name, path)
                calls_by_function.setdefault(node.name, set()).update(_call_names(node))
    return command_defs, registered, calls_by_function


def _reachable_commands(registered: set[str], calls_by_function: dict[str, set[str]]) -> set[str]:
    reachable: set[str] = set()
    seen: set[str] = set()
    stack = list(registered)
    while stack:
        name = stack.pop()
        if name in seen:
            continue
        seen.add(name)
        if name.startswith("command_"):
            reachable.add(name)
        stack.extend(sorted(calls_by_function.get(name, set()) - seen))
    return reachable


def _command_argparse_findings(hydra: Path, root: Path) -> list[Finding]:
    command_defs, registered, calls_by_function = _discover_commands(implementation_source_files(hydra))
    reachable = _reachable_commands(registered, calls_by_function)
    findings: list[Finding] = []
    for name in sorted(set(command_defs) - reachable):
        path = command_defs[name]
        findings.append(Finding(
            path=display_path(path, root),
            code="capability-callers:command-argparse",
            detail=f"{display_path(path, root)} defines `{name}` with no argparse caller",
        ))
    for name in sorted(item for item in reachable if item not in command_defs):
        findings.append(Finding(
            path=display_path(hydra / "scripts" / "hydra.py", root),
            code="capability-callers:command-argparse",
            detail=f"{display_path(hydra / 'scripts' / 'hydra.py', root)} registers `{name}` but no such command exists",
        ))
    return findings


def _evidence_error(path: Path, root: Path, detail: str) -> Finding:
    return Finding(path=display_path(path, root), code="capability-callers:evidence", detail=detail)


def _parse_evidence_file(path: Path, root: Path) -> tuple[dict, list[Finding]]:
    if not path.exists():
        return {}, [_evidence_error(path, root, f"{display_path(path, root)}: file not found")]
    data: dict[str, object] = {"mechanisms": {}}
    mechanisms: dict[str, dict] = data["mechanisms"]  # type: ignore[assignment]
    current_name = ""
    current_field = ""
    current_ref = ""

    for number, raw in enumerate(read_text(path).splitlines(), start=1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        text = raw.strip()
        if indent == 0:
            if text.startswith("schema:"):
                data["schema"] = text.partition(":")[2].strip()
            elif text != "mechanisms:":
                return {}, [_evidence_error(path, root, f"{display_path(path, root)}:{number}: expected `schema` or `mechanisms`")]
        elif indent == 2 and text.endswith(":"):
            current_name = text[:-1]
            mechanisms[current_name] = {"implementation": {}, "callers": {}}
            current_field = ""
            current_ref = ""
        elif indent == 4 and current_name:
            key, sep, value = text.partition(":")
            if not sep:
                return {}, [_evidence_error(path, root, f"{display_path(path, root)}:{number}: expected mechanism field")]
            if key in {"implementation", "callers"} and not value.strip():
                current_field = key
                current_ref = ""
            else:
                mechanisms[current_name][key] = value.strip()
        elif indent == 6 and current_name and current_field in {"implementation", "callers"} and text.endswith(":"):
            current_ref = text[:-1]
            mechanisms[current_name][current_field][current_ref] = []
        elif indent == 8 and current_name and current_field in {"implementation", "callers"} and current_ref and text.startswith("- "):
            mechanisms[current_name][current_field][current_ref].append(text[2:].strip())
        else:
            return {}, [_evidence_error(path, root, f"{display_path(path, root)}:{number}: unsupported capability-caller evidence shape")]
    return data, []


def _snippet_findings(path: Path, root: Path, mechanism_name: str, field: str, refs: dict[str, list[str]]) -> list[Finding]:
    findings: list[Finding] = []
    if not refs:
        return [_evidence_error(path, root, f"{display_path(path, root)} mechanism `{mechanism_name}` missing `{field}` refs")]
    for rel, needles_raw in sorted(refs.items()):
        ref_path = root / str(rel)
        if not ref_path.exists():
            findings.append(_evidence_error(path, root, f"{display_path(path, root)} mechanism `{mechanism_name}` points at missing {rel}"))
            continue
        ref_text = read_text(ref_path)
        needles = [str(needle) for needle in needles_raw]
        if not needles:
            findings.append(_evidence_error(path, root, f"{display_path(path, root)} mechanism `{mechanism_name}` has no snippets for {rel}"))
        for needle in needles:
            if needle not in ref_text:
                findings.append(_evidence_error(
                    path, root, f"{display_path(path, root)} mechanism `{mechanism_name}`: {rel} does not contain `{needle}`"
                ))
    return findings


def _evidence_file_findings(path: Path, root: Path) -> list[Finding]:
    data, parse_findings = _parse_evidence_file(path, root)
    if parse_findings:
        return parse_findings
    if data.get("schema") != SCHEMA:
        return [_evidence_error(path, root, f"{display_path(path, root)} schema must be `{SCHEMA}`")]

    mechanisms = data.get("mechanisms") if isinstance(data.get("mechanisms"), dict) else {}
    if not mechanisms:
        return [_evidence_error(path, root, f"{display_path(path, root)} missing `mechanisms`")]

    findings: list[Finding] = []
    for name, raw in sorted(mechanisms.items()):
        mechanism = raw if isinstance(raw, dict) else {}
        classification = str(mechanism.get("classification", ""))
        if classification not in VALID_CLASSIFICATIONS:
            findings.append(_evidence_error(
                path,
                root,
                f"{display_path(path, root)} mechanism `{name}` classification must be one of "
                "`automatic`, `manual`, or `intentionally-disabled`",
            ))
        implementation = mechanism.get("implementation") if isinstance(mechanism.get("implementation"), dict) else {}
        callers = mechanism.get("callers") if isinstance(mechanism.get("callers"), dict) else {}
        findings.extend(_snippet_findings(path, root, name, "implementation", implementation))
        findings.extend(_snippet_findings(path, root, name, "callers", callers))
    return findings


def validate_capability_callers(hydra: Path, root: Path) -> list[Finding]:
    findings = _command_argparse_findings(hydra, root)
    findings.extend(_evidence_file_findings(hydra / "validation" / "capability-callers.yaml", root))
    return findings
