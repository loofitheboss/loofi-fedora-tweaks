"""
Backward-compatibility shim. CommandRunner has moved to utils.command_runner.
This module will be removed in a future version.
"""

import warnings
warnings.warn(
    "services.system.process is deprecated, use utils.command_runner instead",
    DeprecationWarning,
    stacklevel=2
)

# Import from utils since that's where CommandRunner actually lives
import sys
sys.path.insert(0, '/workspaces/loofi-fedora-tweaks/loofi-fedora-tweaks')
from utils.command_runner import CommandRunner  # noqa: F401
