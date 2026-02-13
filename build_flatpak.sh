#!/bin/bash
set -euo pipefail

exec bash scripts/build_flatpak.sh "$@"
