# v30.0 Architecture Blueprint (P2 DESIGN)

## 1) Scope and Constraints
- Input source: `.workflow/specs/tasks-v30.0.md`.
- This blueprint covers TASK-001..TASK-012 and provides implementation-ready signatures and structures.
- Fedora guardrails applied:
  - UI code untouched (no BaseTab impact in this version).
  - No `sudo`; privileged operations remain `pkexec`-based.
  - No hardcoded `dnf` in Python logic; package manager detection remains via `SystemManager.get_package_manager()` where package manager selection is needed.
  - `PrivilegedCommand` tuple shape remains `(binary, args, description)` and must be unpacked by executors.

## 2) Dependency Graph Validation
- Declared dependencies:
  - TASK-005 -> TASK-004
  - TASK-008 -> TASK-001, TASK-002, TASK-003
  - TASK-009 -> TASK-005
  - TASK-010 -> TASK-006, TASK-007
  - TASK-011 -> TASK-001, TASK-002, TASK-003, TASK-008, TASK-009, TASK-010
  - TASK-012 -> TASK-011
- Topological order (valid, acyclic):
  - TASK-001, TASK-002, TASK-003, TASK-004, TASK-006, TASK-007
  - TASK-005
  - TASK-008, TASK-009, TASK-010
  - TASK-011
  - TASK-012
- Blocking concerns: none. DAG is implementable.

## 3) Architecture Risks and Mitigations

### R1: Packaging scripts become non-deterministic or environment-fragile
- Affected: TASK-001, TASK-002, TASK-003, TASK-008.
- Risk: output names/paths vary by host state; CI reproducibility degrades.
- Mitigation:
  - Explicit `OUTPUT_DIR` and normalized version extraction (`version.py`).
  - `set -euo pipefail` in all packaging scripts.
  - deterministic artifact naming:
    - Flatpak bundle: `loofi-fedora-tweaks-v<version>.flatpak`
    - AppImage: `loofi-fedora-tweaks-v<version>-x86_64.AppImage`
    - sdist: standard `dist/loofi_fedora_tweaks-<version>.tar.gz` (PEP build backend output)
  - Preflight checks with clear non-zero exits.

### R2: Update pipeline trusts remote metadata too loosely
- Affected: TASK-004, TASK-009.
- Risk: incorrect asset selection or integrity bypass.
- Mitigation:
  - Fail-closed verification contract: checksum/signature mismatch returns explicit failure and no install handoff.
  - Strict structured return models (`UpdateAsset`, `DownloadResult`, `VerifyResult`).
  - Network and parse errors mapped to stable error messages.

### R3: Offline-mode ambiguity across marketplace/update paths
- Affected: TASK-005, TASK-009.
- Risk: unhandled exceptions or inconsistent behavior between modules.
- Mitigation:
  - Standardized offline result semantics in both modules: `success=False`, `offline=True`, cache-first fallback if available.
  - Preserve backward compatibility: existing fields remain available.

### R4: Concurrency regressions in limiter/tuner
- Affected: TASK-006, TASK-007, TASK-010.
- Risk: busy-wait CPU churn, history file race/truncation, flaky tests.
- Mitigation:
  - `threading.Event`-based waiting in limiter with computed sleep bound.
  - `threading.RLock` around auto-tuner history read/append/write path.
  - Deterministic concurrency tests with bounded joins/timeouts.

### R5: CI hardening may fail repository immediately
- Affected: TASK-011.
- Risk: raising gates (mypy/bandit/coverage 75) can break PR flow abruptly.
- Mitigation:
  - Remove `continue-on-error` for mypy/bandit in same change as required fixes.
  - Add packaging jobs as artifact/reporting jobs with precise tool checks and clear logs.
  - Keep coverage gate change in same commit as new tests.

## 4) Exact Signatures and Data Structures

### 4.1 `utils/update_checker.py` (TASK-004, TASK-005)
- Keep existing public compatibility:
  - `class UpdateInfo` remains importable.
  - `UpdateChecker.parse_version(version_str: str) -> Tuple[int, ...]`
  - `UpdateChecker.check_for_updates(timeout: int = 10) -> Optional[UpdateInfo]`
- Extend model and API (backward-compatible defaults):

```python
@dataclass
class UpdateAsset:
    name: str
    download_url: str
    size: int = 0
    content_type: str = ""
    checksum_sha256: str = ""
    signature_url: Optional[str] = None

@dataclass
class VerifyResult:
    ok: bool
    method: str
    error: Optional[str] = None

@dataclass
class DownloadResult:
    ok: bool
    file_path: Optional[str] = None
    bytes_written: int = 0
    error: Optional[str] = None

@dataclass
class UpdateInfo:
    current_version: str
    latest_version: str
    release_notes: str
    download_url: str
    is_newer: bool
    assets: List[UpdateAsset] = field(default_factory=list)
    selected_asset: Optional[UpdateAsset] = None
    offline: bool = False
    source: str = "network"  # network|cache
```

- New/updated methods:

```python
@staticmethod
def check_for_updates(timeout: int = 10, use_cache: bool = True) -> Optional[UpdateInfo]: ...

@staticmethod
def select_download_asset(
    assets: List[UpdateAsset],
    preferred_ext: Tuple[str, ...] = (".rpm", ".flatpak", ".AppImage", ".tar.gz"),
) -> Optional[UpdateAsset]: ...

@staticmethod
def download_update(asset: UpdateAsset, target_dir: str, timeout: int = 30) -> DownloadResult: ...

@staticmethod
def verify_download(
    file_path: str,
    expected_sha256: str = "",
    signature_path: Optional[str] = None,
    public_key_path: Optional[str] = None,
) -> VerifyResult: ...
```

- Behavioral contract:
  - Any network/parse/integrity failure => non-raising failure object or `None` from `check_for_updates`.
  - Verification failure blocks install handoff.

### 4.2 `utils/plugin_marketplace.py` (TASK-005)
- Preserve existing `MarketplaceResult` usage, extend with offline metadata:

```python
@dataclass
class MarketplaceResult:
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    offline: bool = False
    source: str = "network"  # network|cache
```

- `PluginMarketplace.fetch_index(force_refresh: bool = False) -> MarketplaceResult`
  - cache-first fallback when network/CDN/GitHub fetch fails.
  - when returning cached fallback due to network failure: `success=True`, `offline=True`, `source="cache"`.
  - when no cache and network unavailable: `success=False`, `offline=True`, stable error text.

### 4.3 `utils/rate_limiter.py` (TASK-006)
- Class contract remains: `TokenBucketRateLimiter(rate: float, capacity: int)`.
- Internal additions:

```python
self._wait_event: threading.Event
```

- Method signatures unchanged:

```python
def acquire(self, tokens: int = 1) -> bool: ...
def wait(self, tokens: int = 1, timeout: float = 5.0) -> bool: ...
@property
def available_tokens(self) -> float: ...
```

- Behavioral changes:
  - `wait()` computes next wake delay from deficit/rate instead of fixed 50ms polling.
  - uses `Event.wait(timeout=...)` to avoid busy loops and reduce CPU churn.

### 4.4 `utils/auto_tuner.py` (TASK-007)
- Public signatures remain stable:

```python
@staticmethod
def detect_workload() -> WorkloadProfile: ...
@staticmethod
def recommend(workload: Optional[WorkloadProfile] = None) -> TuningRecommendation: ...
@staticmethod
def get_tuning_history() -> List[TuningHistoryEntry]: ...
@staticmethod
def save_tuning_entry(entry: TuningHistoryEntry) -> None: ...
```

- Internal synchronization:

```python
_HISTORY_LOCK = threading.RLock()
```

- Required guarded critical sections:
  - file read/parse in `get_tuning_history`
  - append/trim/write in `save_tuning_entry`
  - optional shared-state snapshots if new cached fields are introduced

- Fedora/privilege guardrail for apply methods:
  - retain tuple return shape `(binary, args, description)`.
  - if introducing new privileged paths, prefer `PrivilegedCommand` helpers and never shell-join command strings at call sites.

## 5) Packaging Script Blueprint

### 5.1 `scripts/build_flatpak.sh` and root `build_flatpak.sh` wrapper (TASK-001)
- `scripts/build_flatpak.sh`: source of truth.
- root `build_flatpak.sh`: thin delegator (`exec bash scripts/build_flatpak.sh "$@"`).
- Required checks:
  - tools: `flatpak-builder`, `flatpak`, `tar`.
  - manifest exists: `org.loofi.FedoraTweaks.yml`.
- Required outputs:
  - local repo dir under `dist/flatpak/repo`
  - bundle file under `dist/flatpak/loofi-fedora-tweaks-v<version>.flatpak`
- Exit rules:
  - missing deps/manifest => exit 1 with clear error
  - successful build => exit 0

### 5.2 `scripts/build_appimage.sh` (TASK-002)
- Required checks:
  - tools: `appimagetool`, `linuxdeploy` (or defined fallback path).
- Required outputs:
  - `dist/appimage/loofi-fedora-tweaks-v<version>-x86_64.AppImage`
- Build structure:
  - create clean temp AppDir under `/tmp` or `mktemp -d`
  - populate launcher/desktop/icon + app payload
  - run `appimagetool` with deterministic output name

### 5.3 `scripts/build_sdist.sh` + `pyproject.toml` (TASK-003)
- `pyproject.toml` must define:
  - `[build-system]` with setuptools backend
  - `[project]` name/version metadata compatible with existing package naming
- Script flow:
  - precheck: `python3`, module `build`
  - run: `python3 -m build --sdist --outdir dist`
  - verify expected tarball exists

## 6) CI Blueprint (`.github/workflows/ci.yml`) (TASK-011)
- Convert mypy and bandit to blocking checks:
  - remove `continue-on-error: true`.
- Coverage gate:
  - `--cov-fail-under=75`.
- Add packaging jobs:
  - `package_flatpak`: runs script with dependency checks; upload artifacts if built.
  - `package_appimage`: runs script with dependency checks; upload artifacts if built.
  - `package_sdist`: always runnable on CI Python image; uploads `dist/*.tar.gz`.
- Keep existing core jobs (`lint`, `test`, `security`, `typecheck`) but enforce failure semantics.

## 7) Test Design Contract
- `tests/test_packaging_scripts.py` (new):
  - success and failure path coverage for all 3 scripts.
  - mock shell/tool checks and command composition.
- `tests/test_update_checker.py` (extend):
  - online success, network failure, checksum mismatch, signature mismatch, offline cache path.
- `tests/test_plugin_marketplace_cdn.py` (extend):
  - offline cache-hit success and offline cache-miss failure semantics.
- `tests/test_rate_limiter.py` (new):
  - bounded waits and no busy-spin assumptions under parallel callers.
- `tests/test_auto_tuner.py` (extend):
  - concurrent `save_tuning_entry`/`get_tuning_history` consistency.

## 8) Implementation Notes by Task
- TASK-001/002/003: shell implementation only; avoid introducing Python wrappers unless needed by tests.
- TASK-004/005: keep public API compatibility while adding fields/methods.
- TASK-006/007: internal synchronization only; no breaking interface changes.
- TASK-011: CI gate hardening lands after tests for new behavior exist.
- TASK-012: docs update should reference delivered behavior, not planned behavior.

## 9) Blocking Review Checklist
- [x] Fedora patterns reviewed and respected for affected areas.
- [x] Dependency graph validated as acyclic.
- [x] High-risk changes include explicit mitigations.
- [x] Signatures/data models defined with backward compatibility.
- [x] No unresolved blocking concerns.
