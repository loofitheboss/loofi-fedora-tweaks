#!/usr/bin/env python3
"""Count untimed subprocess calls per file."""
import collections
import os
import re

counter = collections.Counter()
for d in ['loofi-fedora-tweaks/utils', 'loofi-fedora-tweaks/cli']:
    for root, dirs, files in os.walk(d):
        for f in files:
            if f.endswith('.py'):
                fp = os.path.join(root, f)
                with open(fp) as fh:
                    for line in fh:
                        if re.search(r'subprocess\.(run|check_output|Popen|call)\(', line) and 'timeout' not in line:
                            counter[fp] += 1
for fp, c in counter.most_common():
    print(f'{c:3d}  {fp}')
print(f'Total: {sum(counter.values())} calls in {len(counter)} files')
