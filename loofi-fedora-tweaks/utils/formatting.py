"""
Shared formatting utilities for Loofi Fedora Tweaks.
Part of v10.0 "Zenith Update".

Consolidates duplicate bytes_to_human() and other formatters
found across 4+ files.
"""


def bytes_to_human(num_bytes, suffix="B"):
    """Convert bytes to human-readable string (e.g. 1.5 GiB)."""
    for unit in ("", "Ki", "Mi", "Gi", "Ti", "Pi"):
        if abs(num_bytes) < 1024.0:
            return f"{num_bytes:.1f} {unit}{suffix}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} Ei{suffix}"


def seconds_to_human(seconds):
    """Convert seconds to human-readable duration string."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        m, s = divmod(int(seconds), 60)
        return f"{m}m {s}s"
    else:
        h, remainder = divmod(int(seconds), 3600)
        m, s = divmod(remainder, 60)
        return f"{h}h {m}m {s}s"


def percent_bar(value, width=20, fill="=", empty=" "):
    """Create a text-based progress bar like [======    ] 60%."""
    filled = int(width * value / 100)
    bar = fill * filled + empty * (width - filled)
    return f"[{bar}] {value:.0f}%"


def truncate(text, max_len=80, suffix="..."):
    """Truncate text to max length with suffix."""
    if len(text) <= max_len:
        return text
    return text[: max_len - len(suffix)] + suffix
