# Architecture Blueprint — v30.0.0 (P2 DESIGN)

## 1) Scope and Constraints
- In-scope tasks: `TASK-001`..`TASK-015` from `.workflow/specs/tasks-v30.0.0.md`.
- This phase defines implementation contracts only (no code changes in this artifact).
- Fedora guardrails to preserve in implementation:
  - UI code continues to use `BaseTab`; no new subprocess in UI modules.
  - Privileged command tuples must be unpacked before execution: `[binary] + args`.
  - Package-manager-sensitive behavior must use `SystemManager.get_package_manager()` (never hardcode `dnf` in Python logic).

## 2) Dependency Graph (Acyclic)
- Packaging lane:
  - `TASK-001 -> TASK-002`
  - `TASK-003 -> TASK-004`
  - `TASK-005 -> TASK-006`
- Reliability lane:
  - `TASK-007 -> TASK-008 -> TASK-009 -> TASK-010`
  - `TASK-011 -> TASK-012`
- Pipeline + release lane:
  - `TASK-002, TASK-004, TASK-006, TASK-008, TASK-010, TASK-012 -> TASK-013 -> TASK-014 -> TASK-015`
- No cycles detected; all dependencies are implementable in topological order.

## 3) Implementation Contracts by Workstream

### 3.1 Packaging Hardening (`TASK-001`..`TASK-006`)

#### 3.1.1 Flatpak script contract (`scripts/build_flatpak.sh`)
- Keep deterministic outputs under `dist/flatpak/`.
- Required shell function contracts:
  - `require_tool(tool: str) -> exit 1 on missing dependency`
  - `extract_version() -> prints version from loofi-fedora-tweaks/version.py; exit 1 on parse failure`
  - `main() -> validates manifest, cleans transient dirs, builds bundle, validates artifact exists`
- Required success artifact:
  - `dist/flatpak/loofi-fedora-tweaks-v<version>.flatpak`
- Required failure behavior:
  - Non-zero exit with explicit error for missing tool, missing manifest, or version parse failure.

#### 3.1.2 AppImage script contract (`scripts/build_appimage.sh`)
- Required guard checks:
  - `appimagetool` present.
  - `linuxdeploy` resolved via PATH or `LINUXDEPLOY_BIN` executable.
  - desktop file and icon file exist.
- Required deterministic layout:
  - Build into temp AppDir, emit to `dist/appimage/`.
- Required success artifact:
  - `dist/appimage/loofi-fedora-tweaks-v<version>-x86_64.AppImage`
- Required failure behavior:
  - Non-zero exit for any missing dependency/input and missing output artifact.

#### 3.1.3 sdist contract (`scripts/build_sdist.sh`, `pyproject.toml`)
- Script contract:
  - Hard-fail when `python3` missing.
  - Hard-fail when Python `build` module is unavailable.
  - Clean only the target output tarball for current version (avoid deleting unrelated artifacts).
  - Run `python3 -m build --sdist --outdir dist`.
- Expected artifact:
  - `dist/loofi_fedora_tweaks-<version>.tar.gz`
- `pyproject.toml` packaging contract:
  - Keep `build-system` compatible with `python -m build`.
  - Ensure PEP 621 metadata remains complete (`name`, `version`, `description`, `readme`, `requires-python`, `license`, `authors`).
  - Version must align with `loofi-fedora-tweaks/version.py` during v30 implementation window.

#### 3.1.4 Packaging tests (`tests/test_packaging_scripts.py`)
- Must cover both fail and pass branches with stubbed binaries/files.
- New exact assertions:
  - Flatpak success path asserts final bundle file name includes `-v<version>.flatpak`.
  - AppImage success path asserts final file includes `-v<version>-x86_64.AppImage`.
  - sdist success path asserts `loofi_fedora_tweaks-<version>.tar.gz` existence.
- Keep test isolation: temp PATH/tool shims only; no network and no root.

### 3.2 Auto-Update + Offline Reliability (`TASK-007`..`TASK-010`)

#### 3.2.1 Data contracts (`loofi-fedora-tweaks/utils/update_checker.py`)
- Keep existing dataclasses and add one orchestrator result:

```python
@dataclass
class AutoUpdateResult:
    success: bool
    stage: str  # check|select|download|verify|complete
    update_info: Optional[UpdateInfo] = None
    selected_asset: Optional[UpdateAsset] = None
    download: Optional[DownloadResult] = None
    verify: Optional[VerifyResult] = None
    offline: bool = False
    source: str = "network"  # network|cache
    error: Optional[str] = None
```

- Add explicit stable failure constants:

```python
ERR_NO_UPDATE = "no_update_available"
ERR_NO_ASSET = "no_supported_asset"
ERR_DOWNLOAD_FAILED = "download_failed"
ERR_CHECKSUM_MISMATCH = "checksum_mismatch"
ERR_SIGNATURE_FAILED = "signature_verification_failed"
ERR_NETWORK = "network_unavailable"
```

#### 3.2.2 UpdateChecker method signatures
- Preserve compatibility of current APIs:

```python
@staticmethod
def check_for_updates(timeout: int = 10, use_cache: bool = True) -> Optional[UpdateInfo]: ...

@staticmethod
def select_download_asset(
    assets: List[UpdateAsset],
    preferred_ext: Tuple[str, ...] = (".rpm", ".flatpak", ".AppImage", ".tar.gz"),
) -> Optional[UpdateAsset]: ...
```

- Add orchestration method for task acceptance:

```python
@staticmethod
def run_auto_update(
    artifact_preference: Tuple[str, ...],
    target_dir: str,
    timeout: int = 30,
    use_cache: bool = True,
    expected_sha256: str = "",
    signature_path: Optional[str] = None,
    public_key_path: Optional[str] = None,
) -> AutoUpdateResult: ...
```

- Add channel-aware preference resolver:

```python
@staticmethod
def resolve_artifact_preference(
    package_manager: str,
    explicit_channel: str = "auto",
) -> Tuple[str, ...]:
    # dnf -> (.rpm, .flatpak, .AppImage, .tar.gz)
    # rpm-ostree -> (.flatpak, .AppImage, .rpm, .tar.gz)
```

- Rule: package manager value must come from `SystemManager.get_package_manager()` in CLI flow.

#### 3.2.3 CLI wiring (`loofi-fedora-tweaks/cli/main.py`)
- Add import:

```python
from utils.update_checker import UpdateChecker
```

- Add new command handler signature:

```python
def cmd_self_update(args) -> int: ...
```

- Add parser contract:

```python
update_parser = subparsers.add_parser("self-update", help="Check/download verified Loofi updates")
update_parser.add_argument("action", choices=["check", "run"], default="run", nargs="?")
update_parser.add_argument("--channel", choices=["auto", "rpm", "flatpak", "appimage"], default="auto")
update_parser.add_argument("--download-dir", default="~/.cache/loofi-fedora-tweaks/updates")
update_parser.add_argument("--timeout", type=int, default=30)
update_parser.add_argument("--no-cache", action="store_true")
update_parser.add_argument("--checksum", default="")
update_parser.add_argument("--signature-path")
update_parser.add_argument("--public-key-path")
```

- Dispatch contract:
  - register `"self-update": cmd_self_update` in command map.
  - JSON mode returns structured dict mirroring `AutoUpdateResult`.
  - Text mode prints concise stage + error/success.

#### 3.2.4 Offline behavior contract (`TASK-009`)
- `UpdateChecker`:
  - If network fails and cache exists: return result with `offline=True`, `source="cache"`, deterministic stage and no exception leak.
  - If network fails and cache missing: return structured failure with `offline=True`, `source="network"`, `error=ERR_NETWORK` (or mapped equivalent).
- `PluginMarketplace.fetch_index()`:
  - Keep existing `MarketplaceResult` semantics and enforce stable error text for offline miss path.
  - Cache hit fallback must always set `offline=True`, `source="cache"`.
  - Offline miss must set `offline=True`, `source="network"`, deterministic `error`.

#### 3.2.5 Test contracts (`TASK-008`, `TASK-010`)
- `tests/test_update_checker.py` additions:
  - update available + selected artifact path.
  - no-update path returns `success=False` with `ERR_NO_UPDATE` in orchestration.
  - download failure path returns `ERR_DOWNLOAD_FAILED`.
  - checksum mismatch path returns `ERR_CHECKSUM_MISMATCH`.
  - signature failure path returns `ERR_SIGNATURE_FAILED`.
  - cached offline path sets `offline=True`, `source="cache"`.
- `tests/test_plugin_marketplace.py` additions:
  - cache-hit offline fallback assert `offline/source`.
  - offline miss assert deterministic `error` mapping.

### 3.3 Concurrency Safety (`TASK-011`, `TASK-012`)

#### 3.3.1 Rate limiter (`loofi-fedora-tweaks/utils/rate_limiter.py`)
- Keep public API unchanged:

```python
def acquire(self, tokens: int = 1) -> bool: ...
def wait(self, tokens: int = 1, timeout: float = 5.0) -> bool: ...
@property
def available_tokens(self) -> float: ...
```

- Internal robustness requirements:
  - no busy spin under contention.
  - no deadlock under parallel waits.
  - bounded timeout behavior remains deterministic.

#### 3.3.2 Auto tuner history (`loofi-fedora-tweaks/utils/auto_tuner.py`)
- Keep public signatures unchanged:

```python
@staticmethod
def get_tuning_history() -> List[TuningHistoryEntry]: ...

@staticmethod
def save_tuning_entry(entry: TuningHistoryEntry) -> None: ...
```

- Internal write-safety requirement:
  - perform atomic history file writes (temp file + replace) while holding history lock.
  - preserve `_MAX_HISTORY` truncation at 50.

#### 3.3.3 Concurrency tests
- `tests/test_rate_limiter.py`:
  - assert timeout bound.
  - parallel waits complete (no thread hang).
- `tests/test_auto_tuner.py`:
  - parallel save/read with mocked I/O.
  - consistency check on serialized history structure.

### 3.4 CI/Release Hardening (`TASK-013`, `TASK-014`, `TASK-015`)

#### 3.4.1 Workflow required changes
- `.github/workflows/ci.yml`
  - keep package jobs active: Flatpak/AppImage/sdist.
  - enforce test threshold `--cov-fail-under=75`.
- `.github/workflows/auto-release.yml`
  - remove soft-fail from mypy gate (`|| true` forbidden).
  - remove soft-fail from bandit gate (`|| true` forbidden).
  - enforce `--cov-fail-under=75` in test job.

#### 3.4.2 Coverage closure policy (`TASK-014`)
- Extend tests only in touched reliability/distribution modules:
  - `tests/test_update_checker.py`
  - `tests/test_plugin_marketplace.py`
  - `tests/test_packaging_scripts.py`
  - `tests/test_rate_limiter.py`
  - `tests/test_auto_tuner.py`
- Repo-wide target for this version: `--cov-fail-under=75`.

#### 3.4.3 Docs outputs (`TASK-015`)
- Required docs updates after implementation:
  - `CHANGELOG.md`
  - `README.md`
  - `docs/releases/RELEASE-NOTES-v30.0.0.md`
- Must include verification commands used for release checks.

## 4) Risk Register + Mitigations
- Risk: CLI contract drift due new `self-update` command.
  - Mitigation: add parser + handler + command map in one commit; include JSON and text path tests.
- Risk: Backward compatibility break if `check_for_updates` return type changes.
  - Mitigation: preserve existing method signature/return behavior; add orchestration method instead.
- Risk: flaky concurrency tests.
  - Mitigation: use deterministic timeouts and `join(timeout=...)` with bounded assertions.
- Risk: CI hardening increases failure rate short-term.
  - Mitigation: land coverage-gap tests (`TASK-014`) before enforcing pipeline gates (`TASK-013` merges with dependency chain respected).
- Risk: version mismatch across package metadata.
  - Mitigation: in implementation of `TASK-005`, align `pyproject.toml` with current versioning policy and keep `.spec` alignment checks in release workflow.

## 5) Implementation Order (Concrete)
1. `TASK-001`, `TASK-003`, `TASK-005` (script contracts first).
2. `TASK-002`, `TASK-004`, `TASK-006` (script test coverage).
3. `TASK-007` (auto-update orchestrator + CLI wiring).
4. `TASK-008` (auto-update tests).
5. `TASK-009` (offline normalization in update + marketplace).
6. `TASK-010` (offline regression tests).
7. `TASK-011` (thread-safety fixes).
8. `TASK-012` (concurrency tests).
9. `TASK-013` (workflow gate hardening).
10. `TASK-014` (coverage closure to 75%).
11. `TASK-015` (release docs).

## 6) Blocking Concerns
- None unresolved at design phase.
- All tasks have implementable contracts and acyclic dependencies.
