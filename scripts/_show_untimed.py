#!/usr/bin/env python3
"""Show details of untimed subprocess calls."""
import ast
import os


def show_untimed_in_file(filepath):
    with open(filepath) as f:
        source = f.read()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return
    lines = source.split('\n')
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute):
            if func.attr in ('run', 'check_output', 'call', 'Popen'):
                if isinstance(func.value, ast.Name) and func.value.id == 'subprocess':
                    has_timeout = any(
                        kw.arg == 'timeout' for kw in node.keywords)
                    if not has_timeout:
                        context = '\n'.join(
                            lines[node.lineno-1:node.end_lineno])
                        print(
                            f"\n{filepath}:L{node.lineno}-L{node.end_lineno} [{func.attr}]:")
                        print(context)


for d in ['loofi-fedora-tweaks/utils', 'loofi-fedora-tweaks/cli']:
    for root, dirs, files in os.walk(d):
        for f in sorted(files):
            if f.endswith('.py'):
                show_untimed_in_file(os.path.join(root, f))
