---
name: new-tab
description: Scaffold a new feature tab with utils module, UI tab, and test file following project patterns
---

# New Tab

Scaffold a complete feature tab with all required files and wiring.

## Arguments

- `name` (required): Tab name in lowercase (e.g., "firewall", "bluetooth")

## Steps

1. **Create utils module**: `loofi-fedora-tweaks/utils/{name}.py`
   - Class named `{Name}Manager` with `@staticmethod` methods
   - Return `Tuple[str, List[str], str]` command tuples
   - Use `SystemManager.get_package_manager()` for dnf/rpm-ostree branching
   - Use `PrivilegedCommand` for privileged ops
   - Module-level docstring, Google-style

2. **Create UI tab**: `loofi-fedora-tweaks/ui/{name}_tab.py`
   - Class named `{Name}Tab` inheriting `BaseTab`
   - Use `self.run_command()` to execute utils methods
   - No `subprocess`, no business logic
   - Module-level docstring

3. **Register in MainWindow**: Add lazy loader in `loofi-fedora-tweaks/ui/main_window.py`
   ```python
   "{name}": lambda: __import__("ui.{name}_tab", fromlist=["{Name}Tab"]).{Name}Tab(),
   ```

4. **Create test file**: `tests/test_{name}.py`
   - Test class `Test{Name}Manager`
   - `@patch` decorators only (never context managers)
   - Test both success and failure paths
   - Test both dnf and rpm-ostree paths if applicable
   - Mock at `utils.{name}.subprocess.run`

5. **Run verification**: `just lint && just typecheck && just test-file test_{name}`

## Rules

- Follow all critical rules from CLAUDE.md (no sudo, no shell=True, always timeout)
- Use `from utils.log import get_logger` for logging with `%s` formatting
- Type hints on all public methods
