"""Package-manager-aware install hint helpers."""

from services.system import SystemManager


def build_install_hint(package: str) -> str:
    """Return a user-facing install hint for a package.

    Args:
        package: Package name to suggest.

    Returns:
        Install hint string using the detected package manager.
    """
    package_manager = SystemManager.get_package_manager()
    return f"Install with: pkexec {package_manager} install {package}"
