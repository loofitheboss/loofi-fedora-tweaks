#!/bin/bash
cd "$(dirname "$0")"

# Use local virtualenv if present, but don't fail if absent.
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
fi

# Prefer distro-provided PyQt6/KDE integration over user-site pip wheels.
export PYTHONNOUSERSITE=1
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}$(pwd)/loofi-fedora-tweaks"
python3 -s loofi-fedora-tweaks/main.py
