# Architecture Spec — v39.0.0 "Prism"

## Design Rationale

v23.0 introduced the `services/` layer as the canonical home for system abstraction.
Deprecated shims in `utils/` were left for backward compatibility. After 16 versions,
all consumers should import from `services.*` directly. This eliminates runtime
DeprecationWarnings and reduces the import graph.

## Migration Map

### Import Replacements

| Old Import | New Import |
|-----------|------------|
| `from utils.system import SystemManager` | `from services.system import SystemManager` |
| `from utils.hardware import HardwareManager` | `from services.hardware import HardwareManager` |
| `from utils.bluetooth import BluetoothManager` | `from services.hardware import BluetoothManager` |
| `from utils.disk import DiskManager` | `from services.hardware import DiskManager` |
| `from utils.temperature import TemperatureManager` | `from services.hardware import TemperatureManager` |
| `from utils.processes import ProcessManager` | `from services.system import ProcessManager` |
| `from utils.services import ServiceManager, ...` | `from services.system import ServiceManager, ...` |
| `from utils.hardware_profiles import ...` | `from services.hardware import ...` |

### Shim Removal Order

1. Migrate all production imports (T1, T2)
2. Migrate all test imports (T3)
3. Verify zero DeprecationWarning (T11)
4. Remove shim files (T10)

### setStyleSheet → objectName Strategy

For each inline `setStyleSheet(...)` call:
1. Assign `widget.setObjectName("descriptiveName")` using camelCase naming
2. Add QSS rule `#descriptiveName { ... }` to `modern.qss` (dark) and `light.qss` (light)
3. Remove the `setStyleSheet(...)` call
4. Verify visual appearance in both themes

QSS naming convention: `{tab}{Widget}` e.g. `wizardTitle`, `monitorCpuBar`, `hardwareTempLabel`

## Risk Assessment

- **Migration risk**: LOW — services/ modules already re-export same symbols
- **Style risk**: MEDIUM — visual regression possible if QSS specificity doesn't match inline styles
- **Shim removal risk**: LOW — only after all imports verified migrated

## Validation

- `grep -r "from utils\.\(system\|hardware\|bluetooth\|disk\|temperature\|processes\|services\)" loofi-fedora-tweaks/ --include="*.py"` → 0 matches
- `grep -rn "setStyleSheet" loofi-fedora-tweaks/ui/ --include="*.py"` → 0 matches (in target files)
- `pytest tests/ -W error::DeprecationWarning` → 0 DeprecationWarning failures
- All 4349+ tests pass
