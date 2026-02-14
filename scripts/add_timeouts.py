#!/usr/bin/env python3
"""
Add timeout parameters to all subprocess calls that lack them.
Uses context-aware timeout values based on the command being executed.

Timeout categories (from arch-v35.0.0.md):
- Package operations (dnf, rpm-ostree, flatpak): 600s
- Network queries (ping, curl, nmcli, wget): 30s
- System info queries (lsblk, uname, hostnamectl, lscpu, lspci): 15s
- Service operations (systemctl, loginctl): 60s
- File operations (cp, mv, rm, chmod, chown): 120s
- Container operations (podman, docker): 300s
- VM operations (virsh, qemu, virt-install): 300s
- Default fallback: 60s
"""

import os
import re
import sys

# Timeout categories
TIMEOUT_MAP = {
    # Package managers - 600s
    'dnf': 600, 'rpm-ostree': 600, 'flatpak': 600, 'rpm': 600, 'pip': 600,
    # Network - 30s
    'ping': 30, 'curl': 30, 'nmcli': 30, 'wget': 30, 'ip': 30, 'ss': 30,
    'nmap': 30, 'dig': 30, 'nslookup': 30, 'avahi': 30,
    # System info - 15s
    'lsblk': 15, 'uname': 15, 'hostnamectl': 15, 'lscpu': 15, 'lspci': 15,
    'lsusb': 15, 'cat': 15, 'grep': 15, 'find': 30, 'ls': 15, 'id': 15,
    'whoami': 15, 'hostname': 15, 'uptime': 15, 'free': 15, 'df': 15,
    'du': 30, 'wc': 15, 'head': 15, 'tail': 15, 'stat': 15, 'file': 15,
    'which': 15, 'readlink': 15, 'realpath': 15, 'getent': 15, 'locale': 15,
    'timedatectl': 15, 'loginctl': 15, 'xdpyinfo': 15, 'xrandr': 15,
    'pactl': 15, 'pacmd': 15, 'wpctl': 15, 'pw-cli': 15,
    'gsettings': 15, 'dconf': 15, 'kwriteconfig5': 15, 'kreadconfig5': 15,
    'qdbus': 15, 'dbus-send': 15, 'xdg-mime': 15,
    'mokutil': 15, 'sbctl': 15, 'bootctl': 15, 'efibootmgr': 15,
    'fprintd-list': 15, 'fprintd-enroll': 30, 'fprintd-verify': 30,
    'journalctl': 30, 'coredumpctl': 30, 'last': 15,
    'sysctl': 15, 'modprobe': 15, 'lsmod': 15, 'modinfo': 15,
    'zramctl': 15, 'swapon': 15, 'swapoff': 15, 'mkswap': 15,
    'blkid': 15, 'fdisk': 15, 'parted': 30, 'mount': 30,
    'sensors': 15, 'nvidia-smi': 15, 'glxinfo': 15,
    'xprop': 15, 'xdotool': 15, 'wmctrl': 15,
    'pw-dump': 15, 'pw-top': 15,
    # Services - 60s
    'systemctl': 60, 'firewall-cmd': 60, 'ufw': 60,
    'resolvectl': 30, 'networkctl': 30,
    # File operations - 120s
    'cp': 120, 'mv': 120, 'rm': 120, 'chmod': 120, 'chown': 120,
    'rsync': 300, 'tar': 300, 'gzip': 120, 'xz': 120,
    'install': 120, 'mkdir': 15, 'tee': 30, 'touch': 15,
    # Container - 300s
    'podman': 300, 'docker': 300, 'toolbox': 300, 'distrobox': 300,
    # VM - 300s
    'virsh': 300, 'qemu': 300, 'virt-install': 300, 'vboxmanage': 300,
    # Build/dev - 300s
    'gcc': 300, 'make': 300, 'cmake': 300, 'cargo': 300, 'go': 300,
    'node': 300, 'npm': 300, 'yarn': 300, 'code': 30,
    # Audio/video - 60s
    'parecord': 60, 'parec': 60, 'arecord': 60, 'aplay': 60,
    'ffmpeg': 300, 'vlc': 60,
    # Kernel/boot - 120s
    'grub2-mkconfig': 120, 'dracut': 120, 'mkinitcpio': 120,
    'update-grub': 120, 'grubby': 60,
    # Other util commands
    'ansible': 300, 'ansible-playbook': 600, 'ansible-galaxy': 300,
    'git': 60, 'hg': 60, 'svn': 60,
    'python': 300, 'python3': 300,
    'pkexec': 600,  # pkexec wraps other commands
    'sudo': 600,
    'bash': 120, 'sh': 120, 'zsh': 120,
    'sleep': 30,
    'wl-copy': 15, 'wl-paste': 15, 'xclip': 15, 'xsel': 15,
    'xdg-open': 15,
    'voice': 60, 'espeak': 30, 'piper': 60, 'aplay': 60,
    'bt-device': 30, 'bluetoothctl': 30, 'hcitool': 30,
    'iw': 30, 'iwconfig': 30, 'ethtool': 30,
    'usbguard': 60,
    'snap': 300,
}

DEFAULT_TIMEOUT = 60


def guess_timeout_from_context(line, surrounding_lines):
    """Determine appropriate timeout based on command context."""
    # Check the subprocess call arguments for known commands
    all_context = line + ' ' + ' '.join(surrounding_lines)

    # Check for specific commands in the context
    for cmd, timeout in sorted(TIMEOUT_MAP.items(), key=lambda x: -len(x[0])):
        # Look for the command in quotes or as a variable
        patterns = [
            f'"{cmd}"', f"'{cmd}'", f'["{cmd}"', f"['{cmd}'",
            f'"{cmd}",', f"'{cmd}',",
            f'/{cmd}"', f"/{cmd}'",
            f', "{cmd}"', f", '{cmd}'",
        ]
        for pat in patterns:
            if pat in all_context:
                return timeout

    return DEFAULT_TIMEOUT


def add_timeouts_to_file(filepath):
    """Add timeout parameter to subprocess calls in a file."""
    with open(filepath, 'r') as f:
        content = f.read()

    lines = content.split('\n')
    modified = False
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check if this line has a subprocess call without timeout
        if re.search(r'subprocess\.(run|check_output|Popen|call)\(', line) and 'timeout' not in line:
            # Get surrounding context (up to 10 lines ahead)
            surrounding = lines[max(0, i-3):min(len(lines), i+15)]

            # Find the closing parenthesis for this call
            # We need to track parenthesis depth
            paren_depth = 0
            started = False
            close_line = i

            for j in range(i, min(len(lines), i + 30)):
                for ch in lines[j]:
                    if ch == '(':
                        paren_depth += 1
                        started = True
                    elif ch == ')':
                        paren_depth -= 1
                        if started and paren_depth == 0:
                            close_line = j
                            break
                if started and paren_depth == 0:
                    break

            timeout_val = guess_timeout_from_context(line, surrounding)

            # Special handling for Popen - skip timeout for Popen as it doesn't
            # take timeout parameter the same way. Popen.wait(timeout) or
            # Popen.communicate(timeout) is the right pattern.
            if 'subprocess.Popen(' in line:
                # For Popen, we'll add a comment about timeout but not the param
                # Actually, Popen doesn't accept timeout directly. Skip Popen.
                i += 1
                continue

            # Add timeout parameter before the closing paren
            close_content = lines[close_line]

            # Find the position of the last closing paren at depth 0
            # Insert timeout= before it
            # Handle single-line and multi-line cases

            if close_line == i:
                # Single line call - insert before last )
                # Find the matching )
                idx = close_content.rfind(')')
                if idx > 0:
                    before = close_content[:idx].rstrip()
                    after = close_content[idx:]
                    if before.endswith(','):
                        lines[close_line] = f'{before} timeout={timeout_val}{after}'
                    else:
                        lines[close_line] = f'{before}, timeout={timeout_val}{after}'
                    modified = True
            else:
                # Multi-line call - add timeout= line before closing )
                # Find indentation of closing line
                indent_match = re.match(r'^(\s*)', close_content)
                indent = indent_match.group(
                    1) if indent_match else '            '

                # Check if the previous line ends with comma
                prev_line = lines[close_line - 1].rstrip()
                if not prev_line.endswith(','):
                    lines[close_line - 1] = prev_line + ','

                # Determine the argument indentation (one level deeper than close paren)
                arg_indent = indent + '    '

                # Check what the closing line looks like
                stripped_close = close_content.strip()
                if stripped_close == ')' or stripped_close.startswith(')'):
                    lines.insert(
                        close_line, f'{arg_indent}timeout={timeout_val},')
                    modified = True
                else:
                    # Closing paren is on same line as last arg
                    idx = close_content.rfind(')')
                    if idx > 0:
                        before = close_content[:idx].rstrip()
                        after = close_content[idx:]
                        if before.endswith(','):
                            lines[close_line] = f'{before} timeout={timeout_val}{after}'
                        else:
                            lines[close_line] = f'{before}, timeout={timeout_val}{after}'
                        modified = True

        i += 1

    if modified:
        with open(filepath, 'w') as f:
            f.write('\n'.join(lines))
        return True
    return False


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    files_modified = 0
    total_fixed = 0

    for d in ['loofi-fedora-tweaks/utils', 'loofi-fedora-tweaks/cli']:
        full_dir = os.path.join(base_dir, d)
        for root, dirs, files in os.walk(full_dir):
            for f in files:
                if f.endswith('.py'):
                    fp = os.path.join(root, f)

                    # Count before
                    with open(fp) as fh:
                        before_count = sum(
                            1 for line in fh
                            if re.search(r'subprocess\.(run|check_output|call)\(', line) and 'timeout' not in line
                        )

                    if before_count > 0:
                        if add_timeouts_to_file(fp):
                            # Count after
                            with open(fp) as fh:
                                after_count = sum(
                                    1 for line in fh
                                    if re.search(r'subprocess\.(run|check_output|call)\(', line) and 'timeout' not in line
                                )
                            fixed = before_count - after_count
                            total_fixed += fixed
                            files_modified += 1
                            rel = os.path.relpath(fp, base_dir)
                            print(
                                f'  {rel}: {before_count} -> {after_count} ({fixed} fixed)')

    print(f'\nTotal: {total_fixed} calls fixed in {files_modified} files')


if __name__ == '__main__':
    main()
