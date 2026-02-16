"""Regression tests for v43 stabilization invariants."""

import ast
import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_ROOT = ROOT / "loofi-fedora-tweaks"


def _load_checker_module():
    module_name = "check_stabilization_rules_v43_test"
    module_path = ROOT / "scripts" / "check_stabilization_rules.py"

    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _function_has_broad_exception(source: str, function_path: str) -> bool:
    tree = ast.parse(source)

    class _BroadExceptFinder(ast.NodeVisitor):
        def __init__(self, target: str):
            self.target = target
            self.stack: list[str] = []
            self.found = False

        def _visit_callable(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
            self.stack.append(node.name)
            try:
                if ".".join(self.stack) == self.target:
                    for child in ast.walk(node):
                        if (
                            isinstance(child, ast.ExceptHandler)
                            and isinstance(child.type, ast.Name)
                            and child.type.id == "Exception"
                        ):
                            self.found = True
                            return
                self.generic_visit(node)
            finally:
                self.stack.pop()

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            self.stack.append(node.name)
            try:
                self.generic_visit(node)
            finally:
                self.stack.pop()

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self._visit_callable(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self._visit_callable(node)

    finder = _BroadExceptFinder(function_path)
    finder.visit(tree)
    return finder.found


class TestV43Stabilization(unittest.TestCase):
    """Validates stabilization-only release invariants for runtime sources."""

    def test_checker_finds_no_runtime_violations(self):
        module = _load_checker_module()
        targets = list(module.iter_python_sources(SOURCE_ROOT))
        violations = module.collect_violations(targets)
        self.assertEqual([], violations)

    def test_ui_runtime_has_no_subprocess_violations(self):
        module = _load_checker_module()
        violations = module.collect_violations(module.iter_python_sources(SOURCE_ROOT / "ui"))
        ui_violations = [v for v in violations if v.rule == "ui-subprocess"]
        self.assertEqual([], ui_violations)

    def test_broad_exception_allowlist_entries_remain_valid(self):
        module = _load_checker_module()
        stale_entries = []

        for rel_path, function_path in sorted(module.ALLOWED_BROAD_EXCEPTIONS):
            source_path = ROOT / rel_path
            if not source_path.exists():
                stale_entries.append(f"{rel_path}:{function_path} (missing file)")
                continue

            source = source_path.read_text(encoding="utf-8")
            if not _function_has_broad_exception(source, function_path):
                stale_entries.append(f"{rel_path}:{function_path} (missing boundary catch)")

        self.assertEqual([], stale_entries)


if __name__ == "__main__":
    unittest.main()
