---
description: Guidelines for testing Loofi Fedora Tweaks code. Loaded when working with test files or test-related tasks.
applyTo: '**/{tests,test_}*'
---

# Testing Guidelines for Loofi Fedora Tweaks

## Framework and Structure

**Testing Framework**: `unittest` + `unittest.mock`

⚠️ **Important**: Despite having `tests/conftest.py`, we use `unittest`, not pytest-style fixtures. The conftest.py only provides minimal PyQt test environment setup.

## Test File Structure

Every test file must follow this structure:

```python
"""
Tests for [module_name]
"""
import unittest
import sys
import os
from unittest.mock import patch, MagicMock, call, mock_open
from subprocess import CalledProcessError

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.[module] import [Class]
from utils.errors import LoofiError, CommandFailedError

class Test[Class](unittest.TestCase):
    """Tests for [Class]."""
    
    def setUp(self):
        """Set up test fixtures if needed."""
        pass
    
    def tearDown(self):
        """Clean up after tests if needed."""
        pass
    
    # Test methods here...

if __name__ == '__main__':
    unittest.main()
```

## Critical Mocking Rules

### Always Mock These
❌ **Never** let these execute for real in tests:

- `subprocess.run`
- `subprocess.check_output`
- `subprocess.Popen`
- `subprocess.call`
- `shutil.which`
- `os.path.exists`
- `os.path.isfile`
- `os.path.isdir`
- `builtins.open`
- `platform.machine()`
- File I/O operations
- Network calls
- Database operations

### Use @patch Decorators (Not Context Managers)

```python
# ✅ Correct - Use decorators
@patch('utils.mymodule.subprocess.run')
@patch('utils.mymodule.shutil.which')
def test_operation(self, mock_which, mock_run):
    mock_which.return_value = '/usr/bin/tool'
    mock_run.return_value = MagicMock(returncode=0)
    # Test code...

# ❌ Wrong - Don't use context managers
def test_operation(self):
    with patch('utils.mymodule.subprocess.run') as mock_run:
        # Test code...
```

### Mock Return Values

```python
# Simple return value
mock_run.return_value = MagicMock(returncode=0, stdout='Success')

# Raising exceptions
mock_run.side_effect = CalledProcessError(1, 'cmd', stderr='Error')

# Multiple calls with different returns
mock_run.side_effect = [
    MagicMock(returncode=0, stdout='First'),
    MagicMock(returncode=1, stdout='Second'),
]

# Mock file reading
mock_open_fn = mock_open(read_data='file content')
with patch('builtins.open', mock_open_fn):
    # Test file reading...
```

## Testing Patterns

### 1. Test Success and Failure Paths

```python
@patch('utils.mymodule.subprocess.run')
def test_operation_success(self, mock_run):
    """Test successful operation."""
    mock_run.return_value = MagicMock(returncode=0, stdout='Success')
    
    result = MyClass.operation()
    
    self.assertIsNotNone(result)
    self.assertEqual(result[0], 'pkexec')

@patch('utils.mymodule.subprocess.run')
def test_operation_failure(self, mock_run):
    """Test operation failure handling."""
    mock_run.side_effect = CalledProcessError(1, 'cmd', stderr='Error')
    
    with self.assertRaises(CommandFailedError):
        MyClass.operation()
```

### 2. Test Both Fedora Variants

```python
@patch('utils.mymodule.SystemManager.is_atomic')
@patch('utils.mymodule.SystemManager.get_package_manager')
@patch('utils.mymodule.subprocess.run')
def test_package_operation_atomic(self, mock_run, mock_get_pm, mock_is_atomic):
    """Test on atomic Fedora (Silverblue/Kinoite)."""
    mock_is_atomic.return_value = True
    mock_get_pm.return_value = 'rpm-ostree'
    mock_run.return_value = MagicMock(returncode=0)
    
    result = MyClass.install_package('foo')
    
    # Should use rpm-ostree
    self.assertIn('rpm-ostree', str(result))

@patch('utils.mymodule.SystemManager.get_package_manager')
@patch('utils.mymodule.subprocess.run')
def test_package_operation_traditional(self, mock_run, mock_get_pm):
    """Test on traditional Fedora Workstation."""
    mock_get_pm.return_value = 'dnf'
    mock_run.return_value = MagicMock(returncode=0)
    
    result = MyClass.install_package('foo')
    
    # Should use dnf
    self.assertIn('dnf', str(result))
```

### 3. Test Edge Cases

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

@patch('utils.mymodule.subprocess.run')
def test_permission_denied(self, mock_run):
    """Test handling of permission errors."""
    mock_run.side_effect = PermissionError("Access denied")
    
    with self.assertRaises(PrivilegeError):
        MyClass.privileged_operation()
```

### 4. Test Operations Tuple Returns

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

## Running Tests

```bash
# All tests
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ -v

# Specific file
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/test_mymodule.py -v

# Specific test
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/test_mymodule.py::TestMyClass::test_operation -v

# With coverage
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ --cov=loofi-fedora-tweaks --cov-report=html
```

## Test Organization

- **File naming**: `test_[module].py` for `utils/[module].py`
- **Class naming**: `Test[ClassName]` for testing `ClassName`
- **Method naming**: `test_[operation]_[scenario]` (e.g., `test_install_package_success`)
- **Docstrings**: Every test method should have a brief docstring

## Coverage Requirements

When adding new code, ensure tests cover:

1. ✅ **Success path**: Normal operation works
2. ✅ **Failure paths**: Errors are handled gracefully
3. ✅ **Edge cases**: Empty inputs, missing files, etc.
4. ✅ **Fedora variants**: Both atomic and traditional (if package ops)
5. ✅ **Permission scenarios**: Root vs non-root operations
6. ✅ **Error types**: Correct exception types raised

## Example: Complete Test File

```python
"""
Tests for utils/example.py
"""
import unittest
import sys
import os
from unittest.mock import patch, MagicMock, call
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
        """Test package installation on atomic Fedora."""
        mock_get_pm.return_value = 'rpm-ostree'
        
        cmd, args, desc = ExampleManager.install_package('foo')
        
        self.assertEqual(cmd, 'pkexec')
        self.assertIn('rpm-ostree', args)
    
    @patch('utils.example.SystemManager.get_package_manager')
    def test_install_traditional(self, mock_get_pm):
        """Test package installation on traditional Fedora."""
        mock_get_pm.return_value = 'dnf'
        
        cmd, args, desc = ExampleManager.install_package('foo')
        
        self.assertEqual(cmd, 'pkexec')
        self.assertIn('dnf', args)

if __name__ == '__main__':
    unittest.main()
```

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

## Test Status

Current test suite: **839+ tests passing**

Goal: Maintain 100% pass rate, add tests for all new code.