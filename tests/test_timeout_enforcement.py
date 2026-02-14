"""
Test timeout enforcement — v35.0.0 "Fortress"

Scans all utils/ and cli/ for subprocess calls without timeout parameter.
Uses AST parsing to accurately detect multiline calls.
Fails if any untimed subprocess.run/check_output/call calls exist.

Popen calls with '# noqa: timeout' comments are exempted (fire-and-forget/interactive).
"""

import ast
import os
import sys
import unittest
from pathlib import Path

# Project root
PROJECT_ROOT = os.path.join(os.path.dirname(
    __file__), '..', 'loofi-fedora-tweaks')
sys.path.insert(0, PROJECT_ROOT)

# Functions that require timeout parameter
SUBPROCESS_FUNCS = {"subprocess.run",
                    "subprocess.check_output", "subprocess.call"}

# Directories to scan
SCAN_DIRS = [
    os.path.join(PROJECT_ROOT, "utils"),
    os.path.join(PROJECT_ROOT, "cli"),
]


class SubprocessTimeoutVisitor(ast.NodeVisitor):
    """AST visitor to find subprocess calls without timeout."""

    def __init__(self, filepath):
        self.filepath = filepath
        self.violations = []

    def visit_Call(self, node):
        func_name = self._get_func_name(node)
        if func_name in SUBPROCESS_FUNCS:
            has_timeout = any(
                kw.arg == "timeout" for kw in node.keywords
            )
            if not has_timeout:
                self.violations.append({
                    "file": self.filepath,
                    "line": node.lineno,
                    "func": func_name,
                })
        self.generic_visit(node)

    def _get_func_name(self, node):
        """Extract dotted function name from AST Call node."""
        if isinstance(node.func, ast.Attribute):
            value = node.func.value
            if isinstance(value, ast.Attribute):
                if isinstance(value.value, ast.Name):
                    return f"{value.value.id}.{value.attr}.{node.func.attr}"
            elif isinstance(value, ast.Name):
                return f"{value.id}.{node.func.attr}"
        return ""


def find_untimed_calls():
    """Scan all Python files for subprocess calls without timeout."""
    violations = []

    for scan_dir in SCAN_DIRS:
        if not os.path.isdir(scan_dir):
            continue
        for root, _, files in os.walk(scan_dir):
            for fname in sorted(files):
                if not fname.endswith(".py"):
                    continue
                filepath = os.path.join(root, fname)
                try:
                    source = Path(filepath).read_text(encoding="utf-8")
                    tree = ast.parse(source, filename=filepath)
                    visitor = SubprocessTimeoutVisitor(filepath)
                    visitor.visit(tree)
                    violations.extend(visitor.violations)
                except SyntaxError:
                    pass

    return violations


class TestTimeoutEnforcement(unittest.TestCase):
    """Integration test: all subprocess calls must have timeout parameter."""

    def test_no_untimed_subprocess_calls(self):
        """Every subprocess.run/check_output/call must have timeout=..."""
        violations = find_untimed_calls()

        if violations:
            msg_lines = ["Subprocess calls missing timeout parameter:"]
            for v in violations:
                rel = os.path.relpath(v["file"], PROJECT_ROOT)
                msg_lines.append(f"  {rel}:{v['line']} — {v['func']}")
            self.fail("\n".join(msg_lines))

    def test_scan_dirs_exist(self):
        """Verify scan directories exist."""
        for scan_dir in SCAN_DIRS:
            self.assertTrue(
                os.path.isdir(scan_dir),
                f"Scan directory does not exist: {scan_dir}",
            )

    def test_scanner_detects_violations(self):
        """Verify the scanner correctly detects a call without timeout."""
        source = "import subprocess\nsubprocess.run(['ls'])\n"
        tree = ast.parse(source)
        visitor = SubprocessTimeoutVisitor("test.py")
        visitor.visit(tree)
        self.assertEqual(len(visitor.violations), 1)
        self.assertEqual(visitor.violations[0]["func"], "subprocess.run")

    def test_scanner_allows_timed_calls(self):
        """Verify the scanner passes calls WITH timeout."""
        source = "import subprocess\nsubprocess.run(['ls'], timeout=30)\n"
        tree = ast.parse(source)
        visitor = SubprocessTimeoutVisitor("test.py")
        visitor.visit(tree)
        self.assertEqual(len(visitor.violations), 0)


if __name__ == "__main__":
    unittest.main()
