# utils/ — Pure utilities and backward-compatibility re-exports
#
# Executor layer has moved to core/executor/ (v23.0 refactor).
# These re-exports maintain backward compatibility — remove in Phase 6.
from core.executor.action_executor import ActionExecutor  # noqa: F401
from core.executor.action_result import ActionResult  # noqa: F401

# NOTE: Plugin management modules (v26.0 Phase 1) should be imported directly:
#   from utils.plugin_marketplace import PluginMarketplace, MarketplaceResult
#   from utils.plugin_installer import PluginInstaller, InstallerResult
# Not added to __init__.py to avoid circular imports with core.plugins
