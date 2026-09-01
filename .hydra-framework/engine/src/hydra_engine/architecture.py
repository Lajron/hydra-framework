"""Architecture enforcement for the Hydra engine.

Eight checks enforce deliberate module boundaries and measured repository
thresholds. Numeric caps are
public constants with boundary tests here, exact-value pins in
test_architecture.py, and threshold-registry coverage in test_thresholds.py.
Raising one must be a visible decision, not silent drift.

Pure AST analysis; imports nothing from the rest of the package, so it runs
against synthetic tmp package trees before `hydra_engine` holds any modules.
"""

from __future__ import annotations

import ast
import dataclasses
from pathlib import Path

MAX_SOURCE_LINES = 400
MAX_TEST_LINES = 600
MAX_FAN_OUT = 8
MAX_COMPOSITION_ROOT_LINES = 200
HIGH_IN_DEGREE_THRESHOLD = 10
HIGH_IN_DEGREE_MAX_LINES = 150

# Check 7 rejects implementation-placeholder package names. No module or
# package path component may match one of these
# (case-insensitive).
BANNED_STEMS = frozenset({
    "impl", "util", "utils", "common", "core", "runtime", "helpers", "misc",
    "shared", "base", "manager", "service", "services", "handler", "handlers",
})

# check 3: layer by top-level subpackage directory. Lower numbers are more
# foundational; imports may go to the same or a lower layer, never higher.
# A loose top-level module (e.g. this file) has layer None and is exempt —
# it is infrastructure the layers sit on, not part of the stack.
LAYER_OF_DIR = {
    "documents": 0, "identity": 0, "ports": 0,
    "objects": 1,
    "knowledge": 2, "wiki": 2, "work": 2, "providers": 2, "seed": 2,
    "intake": 2, "installation": 2, "agent_hooks": 2, "command_output": 2,
    "checks": 3,
    "commands": 4,
    "cli": 5,
}

@dataclasses.dataclass(frozen=True)
class Violation:
    check: str
    module: str
    detail: str

    def __str__(self) -> str:
        return f"[{self.check}] {self.module}: {self.detail}"


@dataclasses.dataclass(frozen=True)
class CheckResult:
    violations: tuple[Violation, ...]

    @property
    def ok(self) -> bool:
        return not self.violations

    def render(self) -> list[str]:
        return [str(v) for v in self.violations]


@dataclasses.dataclass(frozen=True)
class ModuleInfo:
    dotted: str
    path: Path
    lines: int
    layer: int | None
    imports: frozenset[str]


def _count_lines(path: Path) -> int:
    return len(path.read_text().splitlines())


def _dotted_name(package_root: Path, path: Path, package_name: str) -> str:
    parts = list(path.relative_to(package_root).with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join([package_name, *parts]) if parts else package_name


def _layer_of(package_root: Path, path: Path) -> int | None:
    rel = path.relative_to(package_root)
    return LAYER_OF_DIR.get(rel.parts[0]) if len(rel.parts) > 1 else None


def _from_import_base(dotted_module: str, node: ast.ImportFrom, package_name: str) -> str | None:
    """Dotted target of `from BASE import ...`, resolving relative dots."""
    if node.level:
        parts = dotted_module.split(".")
        anchor = parts[: len(parts) - node.level]
        base = ".".join(anchor + node.module.split(".")) if node.module else ".".join(anchor)
    else:
        base = node.module
    if base and (base == package_name or base.startswith(package_name + ".")):
        return base
    return None


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(), filename=str(path))


def _internal_imports(tree: ast.Module, dotted_module: str, package_name: str, known: set[str]) -> set[str]:
    # `from pkg.sub import leaf` resolves to `pkg.sub.leaf` when that's a
    # real submodule, else falls back to `pkg.sub` (a symbol import).
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == package_name or alias.name.startswith(package_name + "."):
                    found.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            base = _from_import_base(dotted_module, node, package_name)
            if base is None:
                continue
            candidates = {f"{base}.{alias.name}" for alias in node.names}
            found.update(candidates & known or {base})
    return found


def discover_modules(package_root: Path, package_name: str) -> dict[str, ModuleInfo]:
    if not package_root.is_dir():
        return {}
    paths = [p for p in sorted(package_root.rglob("*.py")) if "__pycache__" not in p.parts]
    dotted_by_path = {p: _dotted_name(package_root, p, package_name) for p in paths}
    trees_by_path = {p: _parse(p) for p in paths}
    known = set(dotted_by_path.values())
    return {
        dotted_by_path[p]: ModuleInfo(
            dotted=dotted_by_path[p], path=p, lines=_count_lines(p), layer=_layer_of(package_root, p),
            imports=frozenset(_internal_imports(trees_by_path[p], dotted_by_path[p], package_name, known)),
        )
        for p in paths
    }


def _in_degree(modules: dict[str, ModuleInfo]) -> dict[str, int]:
    degree = {name: 0 for name in modules}
    for m in modules.values():
        for target in m.imports:
            if target in degree:
                degree[target] += 1
    return degree


# check 1: module size, with the grandfather ratchet -------------------------

def _size_violations(items: list[tuple[str, Path, int, int]], grandfathered: dict[str, int], repo_root: Path | None) -> list[Violation]:
    violations = []
    for label, path, lines, cap in items:
        rel_key = None
        if repo_root is not None:
            try:
                rel_key = str(path.relative_to(repo_root))
            except ValueError:
                pass
        if rel_key in grandfathered:
            frozen_at = grandfathered[rel_key]
            if lines > frozen_at:
                violations.append(Violation("module-size", label, f"grandfathered at {frozen_at} lines but is now {lines} (may shrink, never grow)"))
            continue
        if lines > cap:
            violations.append(Violation("module-size", label, f"{lines} lines exceeds the {cap}-line cap"))
    return violations


# check 2: acyclic imports (Tarjan SCC) ---------------------------------------

def _tarjan_sccs(graph: dict[str, frozenset[str]]) -> list[list[str]]:
    counter = [0]
    stack: list[str] = []
    lowlink: dict[str, int] = {}
    index: dict[str, int] = {}
    on_stack: dict[str, bool] = {}
    result: list[list[str]] = []

    def strongconnect(node: str) -> None:
        index[node] = lowlink[node] = counter[0]
        counter[0] += 1
        stack.append(node)
        on_stack[node] = True
        for successor in graph.get(node, frozenset()):
            if successor not in graph:
                continue
            if successor not in index:
                strongconnect(successor)
                lowlink[node] = min(lowlink[node], lowlink[successor])
            elif on_stack.get(successor):
                lowlink[node] = min(lowlink[node], index[successor])
        if lowlink[node] == index[node]:
            component = []
            while True:
                w = stack.pop()
                on_stack[w] = False
                component.append(w)
                if w == node:
                    break
            result.append(component)

    for node in graph:
        if node not in index:
            strongconnect(node)
    return result


def check_acyclic(modules: dict[str, ModuleInfo]) -> list[Violation]:
    graph = {dotted: m.imports for dotted, m in modules.items()}
    violations = []
    for component in _tarjan_sccs(graph):
        if len(component) > 1:
            cycle = " -> ".join(sorted(component))
            violations += [Violation("acyclic-imports", member, f"in an import cycle with {len(component) - 1} other module(s): {cycle}") for member in component]
    return violations


# check 3: layer direction -----------------------------------------------------

def check_layer_direction(modules: dict[str, ModuleInfo]) -> list[Violation]:
    violations = []
    for dotted, m in modules.items():
        if m.layer is None:
            continue
        for target in m.imports:
            target_module = modules.get(target)
            if target_module is None or target_module.layer is None:
                continue
            if m.layer < target_module.layer:
                violations.append(Violation("layer-direction", dotted, f"layer {m.layer} imports {target} in layer {target_module.layer} (upward import)"))
    return violations


# check 4: widely-imported vocabulary -------------------------------------------

def check_high_in_degree(modules: dict[str, ModuleInfo]) -> list[Violation]:
    violations = []
    for dotted, degree in _in_degree(modules).items():
        if degree <= HIGH_IN_DEGREE_THRESHOLD:
            continue
        m = modules[dotted]
        if m.imports:
            violations.append(Violation("widely-imported-vocabulary", dotted, f"in-degree {degree} > {HIGH_IN_DEGREE_THRESHOLD} but imports {sorted(m.imports)} internally"))
        if m.lines > HIGH_IN_DEGREE_MAX_LINES:
            violations.append(Violation("widely-imported-vocabulary", dotted, f"in-degree {degree} > {HIGH_IN_DEGREE_THRESHOLD} but is {m.lines} lines (> {HIGH_IN_DEGREE_MAX_LINES}-line cap)"))
    return violations


# check 5: fan-out ---------------------------------------------------------------

def check_fan_out(modules: dict[str, ModuleInfo], composition_root: str | None) -> list[Violation]:
    in_degree = _in_degree(modules)
    violations = []
    top_layer = max(LAYER_OF_DIR.values())
    for dotted, m in modules.items():
        if dotted == composition_root:
            if m.lines > MAX_COMPOSITION_ROOT_LINES:
                violations.append(Violation("fan-out", dotted, f"declared composition root is {m.lines} lines, exceeds the {MAX_COMPOSITION_ROOT_LINES}-line cap"))
            if m.layer is not None and m.layer != top_layer:
                violations.append(Violation("fan-out", dotted, f"declared composition root sits in layer {m.layer}, must sit in the top layer"))
            if in_degree.get(dotted, 0) != 0:
                violations.append(Violation("fan-out", dotted, f"declared composition root has in-degree {in_degree.get(dotted, 0)}, must be 0"))
            continue
        if len(m.imports) > MAX_FAN_OUT:
            violations.append(Violation("fan-out", dotted, f"fan-out {len(m.imports)} exceeds the {MAX_FAN_OUT} cap"))
    return violations


# check 6: test mirror -------------------------------------------------------------

def _defines_a_test(tree: ast.Module) -> bool:
    return any(
        (isinstance(n, ast.FunctionDef) and n.name.startswith("test"))
        or (isinstance(n, ast.ClassDef) and any(isinstance(i, ast.FunctionDef) and i.name.startswith("test") for i in n.body))
        for n in ast.walk(tree)
    )


def _imports_module(tree: ast.Module, module_basename: str) -> bool:
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom):
            if (n.module and n.module.split(".")[-1] == module_basename) or any(a.name == module_basename for a in n.names):
                return True
        elif isinstance(n, ast.Import) and any(a.name.split(".")[-1] == module_basename for a in n.names):
            return True
    return False


def check_test_mirror(modules: dict[str, ModuleInfo], test_unit_root: Path, package_root: Path) -> list[Violation]:
    violations = []
    test_files = {
        str(p.relative_to(test_unit_root)): p
        for p in (sorted(test_unit_root.rglob("test_*.py")) if test_unit_root.is_dir() else [])
        if "__pycache__" not in p.parts
    }

    expected_names: set[str] = set()
    for dotted, m in modules.items():
        if m.path.name == "__init__.py":
            continue
        rel = m.path.relative_to(package_root)
        expected_rel = str(rel.parent / f"test_{rel.name}")
        expected_names.add(expected_rel)
        test_path = test_files.get(expected_rel)
        if test_path is None:
            violations.append(Violation("test-mirror", dotted, f"no {expected_rel} under {test_unit_root.name}/"))
            continue
        tree = _parse(test_path)
        if not _imports_module(tree, m.path.stem):
            violations.append(Violation("test-mirror", dotted, f"{expected_rel} does not import {m.path.stem}"))
        if not _defines_a_test(tree):
            violations.append(Violation("test-mirror", dotted, f"{expected_rel} defines no test"))

    violations += [Violation("test-mirror", name, "orphan test module with no corresponding source module") for name in test_files if name not in expected_names]
    return violations


# check 7: boundary names -------------------------------------------------------

def check_boundary_names(modules: dict[str, ModuleInfo], package_root: Path) -> list[Violation]:
    violations, seen = [], set()
    for m in modules.values():
        rel = m.path.relative_to(package_root)
        stem = None if rel.stem == "__init__" else rel.stem
        for component in list(rel.parts[:-1]) + ([stem] if stem else []):
            if component.lower() in BANNED_STEMS and (key := f"{rel}:{component}") not in seen:
                seen.add(key)
                violations.append(Violation("boundary-names", str(rel), f"path component '{component}' is a banned name"))
    return violations


# check 8: root derivation locality ---------------------------------------------

def _contains_root_derivation(tree: ast.Module) -> bool:
    """True if the AST computes a filesystem root from `__file__` — the
    shape (`Path(__file__)....parents[N]`, repeated `.parent` walks), not
    the string. A docstring merely mentioning a path does not parse to
    this shape at all."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in ("parent", "parents"):
            if any(isinstance(sub, ast.Name) and sub.id == "__file__" for sub in ast.walk(node.value)):
                return True
    return False


def check_root_derivation(modules: dict[str, ModuleInfo], composition_root: str | None) -> list[Violation]:
    return [
        Violation("root-derivation-locality", dotted, "computes a filesystem root from __file__ outside the declared composition root")
        for dotted, m in modules.items()
        if dotted != composition_root and _contains_root_derivation(_parse(m.path))
    ]


# entry point ---------------------------------------------------------------------

def check(
    *,
    package_root: Path,
    package_name: str = "hydra_engine",
    test_unit_root: Path | None = None,
    hydra_shim: Path | None = None,
    composition_root: str | None = None,
    grandfathered: dict[str, int] | None = None,
    repo_root: Path | None = None,
) -> CheckResult:
    """Run all eight checks. `composition_root` is exempted from fan-out and
    root-derivation once it is declared; before that it's `None`.
    `grandfathered` (the one production use of this, `scripts/hydra.py`,
    shrank below `MAX_SOURCE_LINES` and stopped needing it) is a general
    escape hatch for a future module that outgrows the cap before it can be
    split, not currently populated by anything."""
    grandfathered = dict(grandfathered or {})
    modules = discover_modules(package_root, package_name)

    size_items = [(m.dotted, m.path, m.lines, MAX_SOURCE_LINES) for m in modules.values()]
    if hydra_shim is not None and hydra_shim.exists():
        size_items.append((str(hydra_shim), hydra_shim, _count_lines(hydra_shim), MAX_SOURCE_LINES))

    violations: list[Violation] = []
    violations += _size_violations(size_items, grandfathered, repo_root)
    violations += check_acyclic(modules)
    violations += check_layer_direction(modules)
    violations += check_high_in_degree(modules)
    violations += check_fan_out(modules, composition_root)
    if test_unit_root is not None:
        violations += check_test_mirror(modules, test_unit_root, package_root)
        test_modules = discover_modules(test_unit_root, "tests")
        violations += _size_violations([(m.dotted, m.path, m.lines, MAX_TEST_LINES) for m in test_modules.values()], {}, None)
    violations += check_boundary_names(modules, package_root)
    violations += check_root_derivation(modules, composition_root)

    return CheckResult(violations=tuple(violations))
