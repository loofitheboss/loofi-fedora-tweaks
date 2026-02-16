# Testing

Testing guide for Loofi Fedora Tweaks test suite.

---

## Test Suite Metrics

- **Test files**: 193 files
- **Total tests**: 5878+ tests
- **Coverage**: 82% line coverage
- **Framework**: `unittest` + `unittest.mock`
- **Status**: 5878 passing, 35 skipped

---

## Running Tests

### All Tests

```bash
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ -v
```

### Specific File

```bash
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/test_commands.py -v
```

### Specific Test Method

```bash
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/test_commands.py::TestPrivilegedCommand::test_dnf_install -v
```

### With Coverage

```bash
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ --cov=loofi-fedora-tweaks --cov-report=html --cov-fail-under=80
```

Coverage report: `htmlcov/index.html`

---

## Testing Rules

### 1. Framework

**Use unittest, not pytest fixtures**:

```python
import unittest

class TestMyClass(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        pass
    
    def tearDown(self):
        """Clean up after tests."""
        pass
```

Despite having `tests/conftest.py`, we use `unittest` style.

### 2. Use @patch Decorators Only

**Never use context managers** for mocking:

```python
# ✅ Correct — decorator
@patch('utils.mymodule.subprocess.run')
def test_operation(self, mock_run):
    mock_run.return_value = MagicMock(returncode=0)
    # Test code

# ❌ Wrong — context manager
def test_operation(self):
    with patch('utils.mymodule.subprocess.run') as mock_run:
        # Test code
```

### 3. Mock Everything

**Always mock these** — never let them execute:

- `subprocess.run`
- `subprocess.check_output`
- `subprocess.Popen`
- `shutil.which`
- `os.path.exists`
- `os.path.isfile`
- `builtins.open`
- File I/O operations
- Network calls

```python
@patch('utils.mymodule.subprocess.run')
@patch('utils.mymodule.shutil.which')
@patch('utils.mymodule.os.path.exists')
def test_operation(self, mock_exists, mock_which, mock_run):
    mock_exists.return_value = True
    mock_which.return_value = '/usr/bin/tool'
    mock_run.return_value = MagicMock(returncode=0, stdout='OK')
    # Test code
```

### 4. Test Both Success and Failure Paths

```python
@patch('utils.mymodule.subprocess.run')
def test_operation_success(self, mock_run):
    """Test successful operation."""
    mock_run.return_value = MagicMock(returncode=0, stdout='OK')
    result = MyClass.operation()
    self.assertIsNotNone(result)

@patch('utils.mymodule.subprocess.run')
def test_operation_failure(self, mock_run):
    """Test operation failure handling."""
    mock_run.side_effect = subprocess.CalledProcessError(1, 'cmd', stderr='Error')
    with self.assertRaises(CommandFailedError):
        MyClass.operation()
```

### 5. Test Both Fedora Variants

```python
@patch('utils.mymodule.SystemManager.get_package_manager')
@patch('utils.mymodule.subprocess.run')
def test_install_atomic(self, mock_run, mock_get_pm):
    """Test on Atomic Fedora."""
    mock_get_pm.return_value = 'rpm-ostree'
    mock_run.return_value = MagicMock(returncode=0)
    
    result = MyClass.install_package('foo')
    
    # Should use rpm-ostree
    self.assertIn('rpm-ostree', str(result))

@patch('utils.mymodule.SystemManager.get_package_manager')
@patch('utils.mymodule.subprocess.run')
def test_install_traditional(self, mock_run, mock_get_pm):
    """Test on Traditional Fedora."""
    mock_get_pm.return_value = 'dnf'
    mock_run.return_value = MagicMock(returncode=0)
    
    result = MyClass.install_package('foo')
    
    # Should use dnf
    self.assertIn('dnf', str(result))
```

### 6. No Root Required

Tests run in CI without root privileges. All privileged operations must be mocked.

---

## Test File Structure

```python
"""
Tests for utils/mymodule.py
"""
import unittest
import sys
import os
from unittest.mock import patch, MagicMock, call, mock_open
from subprocess import CalledProcessError

# Add parent to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.mymodule import MyClass
from utils.errors import CommandFailedError


class TestMyClass(unittest.TestCase):
    """Tests for MyClass."""
    
    def setUp(self):
        """Set up test fixtures."""
        pass
    
    def tearDown(self):
        """Clean up after tests."""
        pass
    
    @patch('utils.mymodule.subprocess.run')
    def test_operation_success(self, mock_run):
        """Test successful operation."""
        mock_run.return_value = MagicMock(returncode=0, stdout='OK')
        result = MyClass.operation()
        self.assertIsNotNone(result)
        mock_run.assert_called_once()


if __name__ == '__main__':
    unittest.main()
```

---

## Common Test Patterns

### Mock Return Values

```python
# Simple return
mock_run.return_value = MagicMock(returncode=0, stdout='Success')

# Raising exceptions
mock_run.side_effect = CalledProcessError(1, 'cmd', stderr='Error')

# Multiple calls with different returns
mock_run.side_effect = [
    MagicMock(returncode=0, stdout='First'),
    MagicMock(returncode=1, stdout='Second'),
]
```

### Mock File Operations

```python
# Mock file reading
mock_open_fn = mock_open(read_data='file content')
with patch('builtins.open', mock_open_fn):
    # Test file reading

# Mock file existence
@patch('utils.mymodule.os.path.exists')
def test_file_check(self, mock_exists):
    mock_exists.return_value = True
    # Test code
```

### Test Edge Cases

```python
@patch('utils.mymodule.os.path.exists')
def test_missing_file(self, mock_exists):
    """Test handling of missing file."""
    mock_exists.return_value = False
    with self.assertRaises(FileNotFoundError):
        MyClass.read_config()

@patch('utils.mymodule.shutil.which')
def test_missing_tool(self, mock_which):
    """Test handling of missing system tool."""
    mock_which.return_value = None
    with self.assertRaises(FileNotFoundError):
        MyClass.run_tool()
```

### Test Operations Tuple

```python
def test_operation_returns_tuple(self):
    """Test operation returns correct tuple format."""
    result = MyClass.get_operation()
    
    self.assertIsInstance(result, tuple)
    self.assertEqual(len(result), 3)  # (command, args, description)
    self.assertIsInstance(result[0], str)  # command
    self.assertIsInstance(result[1], list)  # args
    self.assertIsInstance(result[2], str)  # description
```

---

## Naming Conventions

- **Test files**: `test_<module>.py` for `utils/<module>.py`
- **Test classes**: `Test<ClassName>` for testing `ClassName`
- **Test methods**: `test_<operation>_<scenario>`
  - `test_install_package_success`
  - `test_install_package_failure`
  - `test_install_package_atomic`

---

## Coverage Requirements

Aim for **80%+ coverage** for new code. Check coverage:

```bash
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ --cov=loofi-fedora-tweaks --cov-report=term-missing
```

### What to Cover

1. ✅ **Success path** — Normal operation works
2. ✅ **Failure paths** — Errors handled gracefully
3. ✅ **Edge cases** — Empty inputs, missing files, etc.
4. ✅ **Fedora variants** — Both atomic and traditional
5. ✅ **Permission scenarios** — Root vs non-root operations
6. ✅ **Error types** — Correct exception types raised

---

## Quality Gates (CI)

All PRs must pass:

### 1. Lint (flake8)

```bash
flake8 loofi-fedora-tweaks/ --max-line-length=150 --ignore=E501,W503,E402,E722,E203
```

**Rules:**
- Max line length: 150
- Ignored: E501 (line too long), W503 (line break before binary operator), E402 (module level import not at top), E722 (bare except)

### 2. Type Check (mypy)

```bash
mypy loofi-fedora-tweaks/ --ignore-missing-imports --no-error-summary --warn-return-any
```

**Current status**: 0 errors (as of v33.0.0)

### 3. Tests (pytest)

```bash
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ -v
```

**Required**: 100% pass rate

### 4. Security Scan (bandit)

```bash
bandit -r loofi-fedora-tweaks/ -ll -ii --skip B103,B104,B108,B310,B404,B603,B602
```

**Skipped rules:**
- B404, B603, B602 — subprocess-related (handled by PrivilegedCommand pattern)
- B103, B104, B108, B310 — intentional patterns

---

## Example: Complete Test File

```python
"""
Tests for utils/example.py
"""
import unittest
import sys
import os
from unittest.mock import patch, MagicMock
from subprocess import CalledProcessError

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.example import ExampleManager
from utils.errors import CommandFailedError


class TestExampleManager(unittest.TestCase):
    """Tests for ExampleManager."""
    
    @patch('utils.example.subprocess.run')
    @patch('utils.example.shutil.which')
    def test_run_tool_success(self, mock_which, mock_run):
        """Test successful tool execution."""
        mock_which.return_value = '/usr/bin/tool'
        mock_run.return_value = MagicMock(returncode=0, stdout='OK')
        
        result = ExampleManager.run_tool()
        
        self.assertIsNotNone(result)
        mock_which.assert_called_once_with('tool')
        mock_run.assert_called_once()
    
    @patch('utils.example.subprocess.run')
    def test_run_tool_failure(self, mock_run):
        """Test tool execution failure."""
        mock_run.side_effect = CalledProcessError(1, 'tool', stderr='Error')
        
        with self.assertRaises(CommandFailedError):
            ExampleManager.run_tool()
    
    @patch('utils.example.shutil.which')
    def test_run_tool_not_found(self, mock_which):
        """Test tool not found."""
        mock_which.return_value = None
        
        with self.assertRaises(FileNotFoundError):
            ExampleManager.run_tool()
    
    @patch('utils.example.SystemManager.get_package_manager')
    def test_install_atomic(self, mock_get_pm):
        """Test on Atomic Fedora."""
        mock_get_pm.return_value = 'rpm-ostree'
        
        cmd, args, desc = ExampleManager.install_package('foo')
        
        self.assertEqual(cmd, 'pkexec')
        self.assertIn('rpm-ostree', args)
    
    @patch('utils.example.SystemManager.get_package_manager')
    def test_install_traditional(self, mock_get_pm):
        """Test on Traditional Fedora."""
        mock_get_pm.return_value = 'dnf'
        
        cmd, args, desc = ExampleManager.install_package('foo')
        
        self.assertEqual(cmd, 'pkexec')
        self.assertIn('dnf', args)


if __name__ == '__main__':
    unittest.main()
```

---

## Common Pitfalls

### ❌ Don't

- Use pytest fixtures (stick to unittest setUp/tearDown)
- Let subprocess calls execute for real
- Use hardcoded paths in assertions
- Forget to test atomic vs traditional Fedora
- Skip testing error paths
- Use context managers for patches

### ✅ Do

- Mock every system call
- Test both success and failure
- Test both Fedora variants
- Use @patch decorators
- Follow naming conventions
- Add descriptive docstrings
- Verify correct exception types

---

## Debugging Tests

### Run with verbose output

```bash
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/test_mymodule.py -v -s
```

### Show full error tracebacks

```bash
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/test_mymodule.py -v --tb=long
```

### Run only failed tests

```bash
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ --lf
```

---

## Next Steps

- [Contributing](Contributing) — Development workflow
- [Architecture](Architecture) — Understand code structure
- [CI/CD Pipeline](CI-CD-Pipeline) — CI test automation
