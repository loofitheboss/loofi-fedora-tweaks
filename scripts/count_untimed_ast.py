#!/usr/bin/env python3
"""Count untimed subprocess calls per file using AST (accurate for multiline calls)."""
import ast
import collections
import os


def count_untimed_in_file(filepath):
    """Count subprocess.run/check_output/call/Popen calls without timeout."""
    with open(filepath) as f:
        source = f.read()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return 0, 0  # total, untimed

    total = 0
    untimed = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute):
            if func.attr in ('run', 'check_output', 'call', 'Popen'):
                if isinstance(func.value, ast.Name) and func.value.id == 'subprocess':
                    total += 1
                    has_timeout = any(
                        kw.arg == 'timeout' for kw in node.keywords)
                    if not has_timeout:
                        untimed += 1
    return total, untimed


def main():
    counter = collections.Counter()
    total_counter = collections.Counter()

    for d in ['loofi-fedora-tweaks/utils', 'loofi-fedora-tweaks/cli']:
        for root, dirs, files in os.walk(d):
            for f in files:
                if f.endswith('.py'):
                    fp = os.path.join(root, f)
                    total, untimed = count_untimed_in_file(fp)
                    if untimed > 0:
                        counter[fp] = untimed
                        total_counter[fp] = total

    for fp, c in counter.most_common():
        t = total_counter[fp]
        print(f'{c:3d}/{t:3d}  {fp}')
    print(
        f'Untimed: {sum(counter.values())} / Total: {sum(total_counter.values())} across {len(counter)} files')


if __name__ == '__main__':
    main()
