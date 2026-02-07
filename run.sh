#!/bin/bash
cd "$(dirname "$0")"
source .venv/bin/activate
export PYTHONPATH=$PYTHONPATH:$(pwd)/loofi-fedora-tweaks
python3 loofi-fedora-tweaks/main.py
