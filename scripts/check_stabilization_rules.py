#!/usr/bin/env python3
"""Stabilization policy checker for runtime Python sources.

Rules:
1. subprocess.run/check_output/call must include timeout=...
2. UI modules must not call subprocess.run/check_output/call/Popen
3. Runtime code must not hardcode executable dnf invocations
4. broad except Exception handlers must be explicitly allowlisted
"""

from __future__ import annotations

import argparse
import ast
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

ROOT = Path(__file__).resolve().parent.parent
SOURCE_ROOT = ROOT / "loofi-fedora-tweaks"

TIMEOUT_FUNCS = {"run", "check_output", "call"}
SUBPROCESS_FUNCS = TIMEOUT_FUNCS | {"Popen"}

ALLOWED_BROAD_EXCEPTIONS = {
    ("loofi-fedora-tweaks/core/workers/base_worker.py", "BaseWorker.run"),
    ("loofi-fedora-tweaks/utils/event_bus.py", "EventBus._invoke_subscriber"),
    ("loofi-fedora-tweaks/utils/daemon.py", "Daemon.run"),
    ("loofi-fedora-tweaks/ui/lazy_widget.py", "LazyWidget.showEvent"),
    ("loofi-fedora-tweaks/utils/error_handler.py", "_log_error"),
    ("loofi-fedora-tweaks/ui/whats_new_dialog.py", "WhatsNewDialog.mark_seen"),
}


@dataclass(frozen=True)
class Violation:
    """Represents a policy violation."""

    rule: str
    path: str
    line: int
    message: str


class _Analyzer(ast.NodeVisitor):
    """AST analyzer for stabilization policy rules."""

    def __init__(self, rel_path: str):
        self.rel_path = rel_path
        self.violations: List[Violation] = []
        self._stack: List[str] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._stack.append(node.name)
        self.generic_visit(node)
        self._stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._stack.append(node.name)
        self.generic_visit(node)
        self._stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._stack.append(node.name)
        self.generic_visit(node)
        self._stack.pop()

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if isinstance(node.type, ast.Name) and node.type.id == "Exception":
            func_name = ".".join(self._stack) if self._stack else "<module>"
            if (self.rel_path, func_name) not in ALLOWED_BROAD_EXCEPTIONS:
                self.violations.append(
                    Violation(
                        rule="broad-exception",
                        path=self.rel_path,
                        line=node.lineno,
                        message=f"except Exception not allowlisted in {func_name}",
                    )
                )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if _is_subprocess_call(node):
            func_name = _subprocess_func_name(node)
            if func_name in TIMEOUT_FUNCS and not _has_timeout_kw(node):
                self.violations.append(
                    Violation(
                        rule="missing-timeout",
                        path=self.rel_path,
                        line=node.lineno,
                        message=f"subprocess.{func_name} call missing timeout",
                    )
                )

            if self.rel_path.startswith("loofi-fedora-tweaks/ui/"):
                self.violations.append(
                    Violation(
                        rule="ui-subprocess",
                        path=self.rel_path,
                        line=node.lineno,
                        message=f"UI layer uses subprocess.{func_name}",
                    )
                )

            if _contains_literal_dnf_cmd(node):
                self.violations.append(
                    Violation(
                        rule="hardcoded-dnf",
                        path=self.rel_path,
                        line=node.lineno,
                        message="hardcoded executable dnf command",
                    )
                )

        if _is_command_worker_call(node) and _command_worker_uses_literal_dnf(node):
            self.violations.append(
                Violation(
                    rule="hardcoded-dnf",
                    path=self.rel_path,
                    line=node.lineno,
                    message="CommandWorker invocation includes literal dnf command",
                )
            )

        self.generic_visit(node)


def _is_subprocess_call(node: ast.Call) -> bool:
    func = node.func
    return (
        isinstance(func, ast.Attribute)
        and isinstance(func.value, ast.Name)
        and func.value.id == "subprocess"
        and func.attr in SUBPROCESS_FUNCS
    )


def _subprocess_func_name(node: ast.Call) -> str:
    assert isinstance(node.func, ast.Attribute)
    return node.func.attr


def _has_timeout_kw(node: ast.Call) -> bool:
    return any(k.arg == "timeout" for k in node.keywords)


def _is_literal_dnf(value: ast.AST) -> bool:
    return isinstance(value, ast.Constant) and value.value == "dnf"


def _contains_literal_dnf_cmd(node: ast.Call) -> bool:
    if not node.args:
        return False

    first = node.args[0]
    if _is_literal_dnf(first):
        return True

    if isinstance(first, (ast.List, ast.Tuple)):
        if first.elts and _is_literal_dnf(first.elts[0]):
            return True

    return False


def _is_command_worker_call(node: ast.Call) -> bool:
    func = node.func
    return isinstance(func, ast.Name) and func.id == "CommandWorker"


def _command_worker_uses_literal_dnf(node: ast.Call) -> bool:
    if not node.args:
        return False

    # CommandWorker("dnf", [..])
    if _is_literal_dnf(node.args[0]):
        return True

    # CommandWorker("pkexec", ["dnf", ...])
    if len(node.args) > 1 and isinstance(node.args[1], (ast.List, ast.Tuple)):
        args_list = node.args[1]
        if args_list.elts and _is_literal_dnf(args_list.elts[0]):
            return True

    return False


def analyze_source(source: str, rel_path: str) -> List[Violation]:
    """Analyze a source string for policy violations."""
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [
            Violation(
                rule="syntax-error",
                path=rel_path,
                line=exc.lineno or 1,
                message=f"unable to parse: {exc.msg}",
            )
        ]

    analyzer = _Analyzer(rel_path)
    analyzer.visit(tree)
    return analyzer.violations


def analyze_file(path: Path, *, root: Path = ROOT) -> List[Violation]:
    """Analyze one Python file."""
    try:
        rel_path = str(path.relative_to(root))
    except ValueError:
        rel_path = str(path)
    source = path.read_text(encoding="utf-8")
    return analyze_source(source, rel_path)


def iter_python_sources(base: Path) -> Iterable[Path]:
    """Iterate Python source files under a base directory."""
    for path in sorted(base.rglob("*.py")):
        if path.is_file():
            yield path


def collect_violations(paths: Iterable[Path] | None = None) -> List[Violation]:
    """Collect policy violations across runtime sources."""
    targets = list(paths) if paths is not None else list(iter_python_sources(SOURCE_ROOT))
    all_violations: List[Violation] = []
    for path in targets:
        all_violations.extend(analyze_file(path))
    return sorted(all_violations, key=lambda v: (v.path, v.line, v.rule, v.message))


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check stabilization policy invariants.")
    parser.add_argument(
        "paths",
        nargs="*",
        help="Optional file or directory paths to check (defaults to loofi-fedora-tweaks/).",
    )
    return parser.parse_args(argv)


def _expand_targets(paths: list[str]) -> list[Path]:
    if not paths:
        return list(iter_python_sources(SOURCE_ROOT))

    targets: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if not path.is_absolute():
            path = ROOT / path
        if path.is_dir():
            targets.extend(iter_python_sources(path))
        elif path.suffix == ".py" and path.exists():
            targets.append(path)
    return sorted(set(targets))


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    args = _parse_args(argv or sys.argv[1:])
    targets = _expand_targets(args.paths)
    violations = collect_violations(targets)

    for v in violations:
        print(f"{v.path}:{v.line}: {v.rule}: {v.message}")

    if violations:
        print(f"[stabilization-check] FAILED ({len(violations)} violations)")
        return 1

    print("[stabilization-check] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
