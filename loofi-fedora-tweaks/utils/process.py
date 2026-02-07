"""
Backward-compatibility shim. CommandRunner has moved to utils.command_runner.
This module will be removed in a future version.
"""

import warnings
warnings.warn(
    "utils.process is deprecated, use utils.command_runner instead",
    DeprecationWarning,
    stacklevel=2
)

from utils.command_runner import CommandRunner  # noqa: F401
