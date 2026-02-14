#!/usr/bin/env python3
"""Debug AST parsing for firewall_manager.py"""
import ast

fp = "loofi-fedora-tweaks/utils/firewall_manager.py"
with open(fp) as f:
    source = f.read()
tree = ast.parse(source)
lines = source.split("\n")
for node in ast.walk(tree):
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        if node.func.attr in ("run", "check_output", "call") and isinstance(node.func.value, ast.Name) and node.func.value.id == "subprocess":
            has_timeout = any(kw.arg == "timeout" for kw in node.keywords)
            end_line = lines[node.end_lineno -
                             1] if node.end_lineno <= len(lines) else "N/A"
            paren_char = end_line[node.end_col_offset -
                                  1] if node.end_col_offset <= len(end_line) else "?"
            print(f"L{node.lineno}-L{node.end_lineno} col_end={node.end_col_offset} paren={paren_char!r} has_timeout={has_timeout}")
