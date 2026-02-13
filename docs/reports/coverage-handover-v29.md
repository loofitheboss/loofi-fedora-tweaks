# Coverage Push Handover — v29/v30 bridge

**Date:** 2026-02-13
**Goal:** Pass `--cov-fail-under=75` coverage gate
**Current (stable run):** 57.83% (2722 passed, 20 skipped; with two known hanging Qt tests ignored)
**Gap to 75%:** 17.17% (~4,523 lines still needed)

---

## Completed Phases

| Phase | Tests Created | Coverage |
|-------|--------------|----------|
| 1 | `test_scheduler.py`, `test_focus_mode.py`, `test_cli_extended_handlers.py` | 64.84% → 65.51% |
| 2 | Extended `test_cli_extended_handlers.py` (health/tuner/snapshot/logs handlers) | 65.51% → 65.92% |
| 3 | `test_journal.py`, `test_pulse_extended.py`, `test_tiling.py`, `test_usbguard.py`, `test_vscode.py` | 65.92% → 67.72% |
| 4 | `test_automation_profiles_extended.py`, `test_ansible_export.py`, `test_ai.py` | Target modules now at `55%`, `82%`, `75%` in focused run |
| 5 | `test_cli_uncovered_handlers.py` (+ existing `test_cli_extended_handlers.py`) | `cli/main.py` improved to `61.3%` in stable full-suite run |

**Suite status (stable run):** 2671 passed, 0 failures, 20 skipped, 46 warnings.

---

## In Progress (Phase 6)

Primary next targets (non-Qt, high ROI):

- `ui/main_window.py` — 469 missed / 526 total (10.8% covered)
- `ui/monitor_tab.py` — 453 missed / 516 total (12.2% covered)
- `ui/network_tab.py` — 374 missed / 416 total (10.1% covered)
- `utils/agent_runner.py` and `utils/network_monitor.py` (still high misses and easier to unit-test than Qt tabs)

### Phase 6 update (this session)

- Added `tests/test_agent_runner_extended.py`
- Added `tests/test_network_monitor_extended.py`
- Focused combined run (`test_agents`, `test_agent_implementations`, `test_pulse_features`, and new tests):
    - `utils/agent_runner.py`: **90%** (up from ~61% in focused baseline)
    - `utils/network_monitor.py`: **88%**
- Stable full-suite run (excluding known hanging GUI tests):
    - **57.00% total coverage**
    - **2638 passed, 20 skipped, 46 warnings**

### Phase 6 continuation (this session)

- Extended `tests/test_plugin_marketplace.py` with review/rating/download/validation/offline branch coverage
- Extended `tests/test_update_checker.py` for remaining verify/signature/error branches
- Extended `tests/test_auto_tuner.py` for helper exception + edge-path coverage
- Extended `tests/test_rate_limiter.py` for immediate wait + `available_tokens` bounded behavior
- Focused module run (`test_update_checker`, `test_plugin_marketplace`, `test_packaging_scripts`, `test_rate_limiter`, `test_auto_tuner`):
    - `utils/update_checker.py`: **100%** (from 92.9% in focused baseline)
    - `utils/plugin_marketplace.py`: **82.6%** (from 51.2%)
    - `utils/rate_limiter.py`: **97.7%** (from 88.6%)
    - `utils/auto_tuner.py`: **97.1%** (from 84.5%)
- Stable full-suite run (excluding known hanging GUI tests):
    - **56.87% total coverage**
    - **2671 passed, 20 skipped, 46 warnings**

### Phase 6 continuation (latest session)

- Added `tests/test_services_hardware_manager.py` for non-Qt coverage of CPU/GPU/fan/power/AI capability paths in `services/hardware/hardware.py`
- Added `tests/test_cli_hardware_plugins_preset.py` for uncovered `cli/main.py` handlers (`cmd_hardware`, `cmd_plugins`, `cmd_preset`)
- Focused coverage runs:
    - `services/hardware/hardware.py`: **77.08%** (from 17.01% in stable baseline)
    - `cli/main.py`: **65.99%** (from 61.33% in stable baseline)
- Stable full-suite run (excluding known hanging GUI tests):
    - **57.83% total coverage**
    - **2722 passed, 20 skipped, 46 warnings**

---

## pkexec Guard

Added a safety net in `tests/conftest.py` that monkey-patches `subprocess.run` and `subprocess.Popen` to block any real `pkexec`/`sudo` calls during tests. This prevents the polkit password dialog from appearing during test runs.

Blocked calls return `returncode=1` with `stderr="blocked by test harness"`.

---

## Known Pre-existing Test Issues

Two test files **hang/timeout** in the full suite (not caused by coverage work):

- `test_main_window_geometry.py` — instantiates `MainWindow`, hangs in offscreen Qt
- `test_frameless_mode_flag.py` — similar Qt widget instantiation hang

These need `--timeout` enforcement or should be skipped outside CI.

---

## Top Remaining Hotspots

```
590 missed / 1735 total = 66.0%  cli/main.py
469 missed /  526 total = 10.8%  ui/main_window.py
453 missed /  516 total = 12.2%  ui/monitor_tab.py
374 missed /  416 total = 10.1%  ui/network_tab.py
342 missed /  386 total = 11.4%  ui/development_tab.py
334 missed /  334 total =  0.0%  ui/agents_tab.py
317 missed /  368 total = 13.9%  ui/dashboard_tab.py
308 missed /  308 total =  0.0%  ui/wizard.py
305 missed /  339 total = 10.0%  ui/virtualization_tab.py
291 missed /  331 total = 12.1%  ui/hardware_tab.py
279 missed /  350 total = 20.3%  ui/ai_enhanced_tab.py
278 missed /  318 total = 12.6%  ui/automation_tab.py
```

---

## Estimate to 75%

Current repo state is much larger than initial v29 baseline; most remaining uncovered code is in UI-heavy modules.
For the next iteration, expect better ROI by targeting testable utility/services modules first, then selective CLI paths.

Priority targets (testable without full Qt instantiation):
1. Remaining `cli/main.py` command families with mocked managers
2. `core/plugins/package.py`, `utils/plugin_marketplace.py`
3. Select service modules still below 80% (non-Qt first)
4. Any low-risk parser/dispatch branches in CLI entrypoints

---

## Commands

```bash
# Run tests
cd "/home/loofi/Dokument/loofi fedora 43 v1/loofi-fedora-tweaks"
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ -q --timeout=30 --cov=loofi-fedora-tweaks --cov-fail-under=75

# Stable run excluding known hanging GUI tests
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ -q --timeout=30 \
    --cov=loofi-fedora-tweaks \
    --ignore=tests/test_main_window_geometry.py \
    --ignore=tests/test_frameless_mode_flag.py

# Coverage JSON for hotspot analysis
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ -q --cov=loofi-fedora-tweaks --cov-report=json:/tmp/loofi_cov.json

# Rank hotspots from JSON
python3 -c "
import json
data = json.load(open('/tmp/loofi_cov.json'))
files = []
for fpath, fdata in data['files'].items():
    missed = fdata['summary']['missing_lines']
    total = fdata['summary']['num_statements']
    if missed > 40:
        pct = fdata['summary']['percent_covered']
        files.append((missed, total, pct, fpath))
files.sort(reverse=True)
for missed, total, pct, fpath in files[:25]:
    short = fpath.split('loofi-fedora-tweaks/')[-1]
    print(f'{missed:4d} missed / {total:4d} total = {pct:5.1f}%  {short}')
"
```
