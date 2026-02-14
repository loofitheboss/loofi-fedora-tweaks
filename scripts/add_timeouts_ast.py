#!/usr/bin/env python3
"""
Add timeout parameters to all subprocess calls that lack them.
Uses Python AST for reliable parsing instead of regex.

Timeout categories (from arch-v35.0.0.md):
- Package operations (dnf, rpm-ostree, flatpak): 600s
- Network queries (ping, curl, nmcli, wget): 30s
- System info queries (lsblk, uname, hostnamectl, etc.): 15s
- Service operations (systemctl, firewall-cmd): 60s
- File operations (cp, mv, rm): 120s
- Container/VM operations (podman, virsh): 300s
- Default fallback: 60s
"""

import ast
import os
import re
import sys

# Command -> timeout mapping
TIMEOUT_MAP = {
    # Package managers - 600s
    'dnf': 600, 'rpm-ostree': 600, 'flatpak': 600, 'rpm': 600, 'pip': 600,
    'pip3': 600, 'pkexec': 600,
    # Network - 30s
    'ping': 30, 'curl': 30, 'nmcli': 30, 'wget': 30, 'ip': 30, 'ss': 30,
    'nmap': 30, 'dig': 30, 'avahi-browse': 30, 'avahi-resolve': 30,
    'resolvectl': 30, 'networkctl': 30,
    # System info - 15s
    'lsblk': 15, 'uname': 15, 'hostnamectl': 15, 'lscpu': 15, 'lspci': 15,
    'lsusb': 15, 'cat': 15, 'grep': 15, 'ls': 15, 'id': 15,
    'whoami': 15, 'hostname': 15, 'uptime': 15, 'free': 15, 'df': 15,
    'stat': 15, 'file': 15, 'which': 15, 'readlink': 15, 'getent': 15,
    'locale': 15, 'timedatectl': 15, 'loginctl': 15,
    'pactl': 15, 'wpctl': 15, 'pw-cli': 15, 'pw-dump': 15,
    'gsettings': 15, 'dconf': 15, 'kwriteconfig5': 15, 'kreadconfig5': 15,
    'qdbus': 15, 'xdg-mime': 15, 'xdg-open': 15,
    'mokutil': 15, 'sbctl': 15, 'bootctl': 15, 'efibootmgr': 15,
    'fprintd-list': 15, 'zramctl': 15, 'swapon': 15, 'swapoff': 15,
    'blkid': 15, 'sensors': 15, 'nvidia-smi': 15, 'glxinfo': 15,
    'xprop': 15, 'wmctrl': 15, 'lsmod': 15, 'modinfo': 15,
    'wl-copy': 15, 'wl-paste': 15, 'xclip': 15, 'xsel': 15,
    'sysctl': 15, 'head': 15, 'tail': 15, 'echo': 15, 'printf': 15,
    'test': 15, 'true': 15, 'false': 15, 'env': 15, 'printenv': 15,
    # Journalctl - 30s
    'journalctl': 30, 'coredumpctl': 30, 'last': 15,
    'find': 30, 'du': 30, 'wc': 15,
    # Service operations - 60s
    'systemctl': 60, 'firewall-cmd': 60, 'ufw': 60,
    'usbguard': 60, 'modprobe': 30,
    # File operations - 120s
    'cp': 120, 'mv': 120, 'rm': 120, 'chmod': 120, 'chown': 120,
    'install': 120, 'mkdir': 15, 'tee': 30, 'touch': 15,
    'rsync': 300, 'tar': 300, 'sed': 30, 'awk': 30,
    # Container/VM - 300s
    'podman': 300, 'docker': 300, 'toolbox': 300, 'distrobox': 300,
    'virsh': 300, 'qemu-img': 300, 'virt-install': 300, 'vboxmanage': 300,
    # Build/dev - 300s
    'code': 30, 'ansible': 300, 'ansible-playbook': 600,
    'git': 60, 'python3': 300, 'python': 300,
    'node': 300, 'npm': 300, 'cargo': 300,
    # Audio - 60s
    'espeak': 30, 'piper': 60, 'aplay': 60, 'arecord': 60,
    # Boot/kernel - 120s
    'grub2-mkconfig': 120, 'dracut': 120, 'grubby': 60,
    # Shell - 120s
    'bash': 120, 'sh': 120, 'zsh': 120,
    # Bluetooth
    'bluetoothctl': 30, 'bt-device': 30,
}

DEFAULT_TIMEOUT = 60


def get_timeout_for_call(node, source_lines):
    """Determine the appropriate timeout value based on the command in the call."""
    # Try to extract command from the first argument
    if node.args:
        first_arg = node.args[0]
        # Handle list literal: subprocess.run(["cmd", ...])
        if isinstance(first_arg, ast.List) and first_arg.elts:
            first_elt = first_arg.elts[0]
            if isinstance(first_elt, ast.Constant) and isinstance(first_elt.value, str):
                cmd = os.path.basename(first_elt.value)
                if cmd in TIMEOUT_MAP:
                    return TIMEOUT_MAP[cmd]
                # Check second element for pkexec wrapping
                if cmd == 'pkexec' and len(first_arg.elts) > 1:
                    second = first_arg.elts[1]
                    if isinstance(second, ast.Constant) and isinstance(second.value, str):
                        inner_cmd = os.path.basename(second.value)
                        if inner_cmd in TIMEOUT_MAP:
                            return TIMEOUT_MAP[inner_cmd]

        # Handle string literal: subprocess.run("cmd ...")
        if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
            cmd = first_arg.value.split()[0] if first_arg.value.strip() else ""
            cmd = os.path.basename(cmd)
            if cmd in TIMEOUT_MAP:
                return TIMEOUT_MAP[cmd]

    # Try to infer from surrounding source
    start = max(0, node.lineno - 3)
    end = min(len(source_lines), node.end_lineno + 2)
    context = ' '.join(source_lines[start:end])

    for cmd, timeout in sorted(TIMEOUT_MAP.items(), key=lambda x: -len(x[0])):
        if f'"{cmd}"' in context or f"'{cmd}'" in context:
            return timeout

    return DEFAULT_TIMEOUT


def has_timeout_kwarg(node):
    """Check if a Call node already has a timeout keyword argument."""
    for kw in node.keywords:
        if kw.arg == 'timeout':
            return True
    return False


def process_file(filepath):
    """Add timeout to subprocess calls in a file. Returns (calls_found, calls_fixed)."""
    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return 0, 0

    source_lines = source.split('\n')
    calls_to_fix = []  # (line, col, end_line, end_col, timeout_val)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        # Check if it's subprocess.run/check_output/call (not Popen)
        func = node.func
        is_subprocess_call = False
        func_name = ""

        if isinstance(func, ast.Attribute):
            if func.attr in ('run', 'check_output', 'call'):
                if isinstance(func.value, ast.Name) and func.value.id == 'subprocess':
                    is_subprocess_call = True
                    func_name = func.attr
                elif isinstance(func.value, ast.Attribute):
                    # Handle cases like module.subprocess.run
                    if func.value.attr == 'subprocess':
                        is_subprocess_call = True
                        func_name = func.attr

        if not is_subprocess_call:
            continue

        if has_timeout_kwarg(node):
            continue

        timeout_val = get_timeout_for_call(node, source_lines)
        calls_to_fix.append({
            'lineno': node.lineno,
            'end_lineno': node.end_lineno,
            'end_col_offset': node.end_col_offset,
            'timeout': timeout_val,
        })

    if not calls_to_fix:
        return 0, 0

    # Apply fixes in reverse order to preserve line numbers
    lines = source_lines[:]
    for fix in reversed(calls_to_fix):
        end_line_idx = fix['end_lineno'] - 1
        end_col = fix['end_col_offset']
        timeout_val = fix['timeout']

        # The call ends at end_col with ')'. We insert timeout= before that ')'
        line_content = lines[end_line_idx]

        # Find the closing ) at end_col - 1
        paren_pos = end_col - 1
        if paren_pos < len(line_content) and line_content[paren_pos] == ')':
            before_paren = line_content[:paren_pos].rstrip()
            after_paren = line_content[paren_pos:]

            # Check if single-line or multi-line
            if fix['lineno'] == fix['end_lineno']:
                # Single line
                if before_paren.endswith(','):
                    lines[end_line_idx] = f'{before_paren} timeout={timeout_val}{after_paren}'
                else:
                    lines[end_line_idx] = f'{before_paren}, timeout={timeout_val}{after_paren}'
            else:
                # Multi-line: add timeout as a new line before the closing )
                # Get indentation of the closing )
                close_indent = len(line_content) - len(line_content.lstrip())

                # Look at previous non-empty line to match arg indentation
                prev_idx = end_line_idx - 1
                while prev_idx >= 0 and not lines[prev_idx].strip():
                    prev_idx -= 1
                if prev_idx >= 0:
                    prev_line = lines[prev_idx]
                    prev_indent = len(prev_line) - len(prev_line.lstrip())
                    arg_indent = ' ' * prev_indent
                else:
                    arg_indent = ' ' * (close_indent + 4)

                # Ensure previous line ends with comma
                prev_stripped = lines[prev_idx].rstrip()
                if not prev_stripped.endswith(','):
                    lines[prev_idx] = prev_stripped + ','

                # Insert timeout line before closing paren
                timeout_line = f'{arg_indent}timeout={timeout_val},'
                lines.insert(end_line_idx, timeout_line)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    return len(calls_to_fix), len(calls_to_fix)


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    total_found = 0
    total_fixed = 0
    files_modified = 0

    for d in ['loofi-fedora-tweaks/utils', 'loofi-fedora-tweaks/cli']:
        full_dir = os.path.join(base_dir, d)
        for root, dirs, files in os.walk(full_dir):
            for f in sorted(files):
                if f.endswith('.py'):
                    fp = os.path.join(root, f)
                    found, fixed = process_file(fp)
                    if found > 0:
                        total_found += found
                        total_fixed += fixed
                        files_modified += 1
                        rel = os.path.relpath(fp, base_dir)
                        print(f'  {rel}: {found} calls fixed (timeout added)')

    print(
        f'\nTotal: {total_fixed}/{total_found} calls fixed in {files_modified} files')

    # Verify remaining
    remaining = 0
    for d in ['loofi-fedora-tweaks/utils', 'loofi-fedora-tweaks/cli']:
        full_dir = os.path.join(base_dir, d)
        for root, dirs, files in os.walk(full_dir):
            for f in files:
                if f.endswith('.py'):
                    fp = os.path.join(root, f)
                    with open(fp) as fh:
                        for line in fh:
                            if re.search(r'subprocess\.(run|check_output|call)\(', line) and 'timeout' not in line:
                                remaining += 1

    print(f'Remaining untimed calls (excluding Popen): {remaining}')


if __name__ == '__main__':
    main()
