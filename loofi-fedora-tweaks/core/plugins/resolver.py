"""
Plugin dependency resolver with version constraint handling.
Part of v26.0 Phase 1 (T8).
"""
import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

try:
    from packaging.version import parse as parse_version  # noqa: F401
    from packaging.specifiers import SpecifierSet  # noqa: F401
    HAS_PACKAGING = True
except ImportError:
    HAS_PACKAGING = False
    logger = logging.getLogger(__name__)
    logger.warning("packaging library not available, using simple version comparison")

logger = logging.getLogger(__name__)


@dataclass
class DependencyError:
    """Error during dependency resolution."""
    plugin_id: str
    error_type: str  # "missing", "conflict", "cycle", "version_mismatch"
    message: str


@dataclass
class ResolverResult:
    """Result of dependency resolution."""
    success: bool
    install_order: List[str]  # Topologically sorted plugin IDs
    errors: List[DependencyError]
    missing: List[str]  # Plugin IDs not installed
    conflicts: List[Tuple[str, str]]  # Conflicting plugin pairs


class DependencyResolver:
    """Resolve plugin dependencies with version constraints."""

    def __init__(self, installed_plugins: Dict[str, str]):
        """
        Initialize resolver with currently installed plugins.

        Args:
            installed_plugins: Dict mapping plugin_id -> version string
        """
        self.installed_plugins = installed_plugins

    @staticmethod
    def _parse_requirement(requirement: str) -> Tuple[str, str, Optional[str]]:
        """
        Parse dependency requirement string.

        Args:
            requirement: String like "plugin-name>=1.0", "plugin-name==2.0", "plugin-name"

        Returns:
            Tuple of (plugin_id, operator, version)
            operator is one of: "==", ">=", "<=", ">", "<", "" (any version)
        """
        # Match patterns: plugin-name>=1.0, plugin-name==2.0, etc.
        match = re.match(r'^([a-z0-9-]+)\s*(>=|<=|==|>|<)?\s*([0-9.]+)?$', requirement.strip())

        if not match:
            logger.warning("Invalid requirement format: %s", requirement)
            return (requirement.strip(), "", None)

        plugin_id = match.group(1)
        operator = match.group(2) or ""
        version = match.group(3)

        return (plugin_id, operator, version)

    @staticmethod
    def _check_version_constraint(installed_version: str, operator: str, required_version: Optional[str]) -> bool:
        """
        Check if installed version satisfies requirement.

        Args:
            installed_version: Version string of installed plugin
            operator: Comparison operator ("==", ">=", etc.)
            required_version: Required version string

        Returns:
            True if constraint satisfied
        """
        if not operator or not required_version:
            return True  # Any version acceptable

        try:
            if HAS_PACKAGING:
                # Use packaging library for proper version comparison
                installed = parse_version(installed_version)
                required = parse_version(required_version)

                if operator == "==":
                    return bool(installed == required)
                elif operator == ">=":
                    return bool(installed >= required)
                elif operator == "<=":
                    return bool(installed <= required)
                elif operator == ">":
                    return bool(installed > required)
                elif operator == "<":
                    return bool(installed < required)
                else:
                    return True
            else:
                # Simple string comparison fallback
                if operator == "==":
                    return installed_version == required_version
                elif operator == ">=":
                    return installed_version >= required_version
                elif operator == "<=":
                    return installed_version <= required_version
                else:
                    return True

        except (ValueError, TypeError, AttributeError) as exc:
            logger.error("Version comparison failed: %s", exc)
            return False

    def get_missing(self, plugin_id: str, requirements: List[str]) -> List[str]:
        """
        Get list of missing dependencies for a plugin.

        Args:
            plugin_id: ID of plugin to check
            requirements: List of requirement strings from plugin manifest

        Returns:
            List of missing plugin IDs
        """
        missing = []

        for req in requirements:
            dep_id, operator, version = self._parse_requirement(req)

            if dep_id not in self.installed_plugins:
                missing.append(dep_id)
                logger.debug("Missing dependency: %s requires %s", plugin_id, dep_id)
            elif version and operator:
                installed_ver = self.installed_plugins[dep_id]
                if not self._check_version_constraint(installed_ver, operator, version):
                    logger.debug("Version mismatch: %s requires %s%s%s (installed: %s)",
                                 plugin_id, dep_id, operator, version, installed_ver)
                    # Treat version mismatch as missing - return just plugin ID
                    missing.append(dep_id)

        return missing

    def check_conflicts(self, plugin_requirements: Dict[str, List[str]]) -> List[Tuple[str, str]]:
        """
        Detect version conflicts between plugins.

        Args:
            plugin_requirements: Dict mapping plugin_id -> list of requirements

        Returns:
            List of conflicting plugin pairs (plugin_a, plugin_b)
        """
        conflicts = []

        # Build version constraints for each dependency
        constraints: Dict[str, List[Tuple[str, str, Optional[str]]]] = {}

        for plugin_id, requirements in plugin_requirements.items():
            for req in requirements:
                dep_id, operator, version = self._parse_requirement(req)

                if dep_id not in constraints:
                    constraints[dep_id] = []

                constraints[dep_id].append((plugin_id, operator, version))

        # Check for conflicting constraints
        for dep_id, reqs in constraints.items():
            if len(reqs) < 2:
                continue

            # Simple conflict detection: exact version mismatches
            exact_versions = [(plugin_id, ver) for plugin_id, op, ver in reqs if op == "==" and ver]

            if len(exact_versions) > 1:
                unique_versions = set(ver for _, ver in exact_versions)
                if len(unique_versions) > 1:
                    # Multiple plugins require different exact versions
                    plugin_a = exact_versions[0][0]
                    plugin_b = exact_versions[1][0]
                    conflicts.append((plugin_a, plugin_b))
                    logger.warning("Conflict: %s and %s require different versions of %s",
                                   plugin_a, plugin_b, dep_id)

        return conflicts

    def resolve(self, plugin_requirements: Dict[str, List[str]]) -> ResolverResult:
        """
        Resolve dependencies and return topologically sorted install order.

        Args:
            plugin_requirements: Dict mapping plugin_id -> list of requirement strings

        Returns:
            ResolverResult with install order or errors
        """
        errors = []
        missing_all = []

        # Handle empty input
        if not plugin_requirements:
            return ResolverResult(
                success=True,
                install_order=[],
                errors=[],
                missing=[],
                conflicts=[]
            )

        try:
            # Check for missing dependencies
            for plugin_id, requirements in plugin_requirements.items():
                missing = self.get_missing(plugin_id, requirements)
                if missing:
                    missing_all.extend(missing)
                    for dep in missing:
                        errors.append(DependencyError(
                            plugin_id=plugin_id,
                            error_type="missing",
                            message=f"Missing dependency: {dep}"
                        ))

            # Check for conflicts
            conflicts = self.check_conflicts(plugin_requirements)
            for plugin_a, plugin_b in conflicts:
                errors.append(DependencyError(
                    plugin_id=plugin_a,
                    error_type="conflict",
                    message=f"Conflict with {plugin_b}"
                ))

            if errors:
                return ResolverResult(
                    success=False,
                    install_order=[],
                    errors=errors,
                    missing=list(set(missing_all)),
                    conflicts=conflicts
                )

            # Perform topological sort
            install_order = self._topological_sort(plugin_requirements)

            if not install_order:
                errors.append(DependencyError(
                    plugin_id="unknown",
                    error_type="cycle",
                    message="Circular dependency detected"
                ))
                return ResolverResult(
                    success=False,
                    install_order=[],
                    errors=errors,
                    missing=[],
                    conflicts=[]
                )

            logger.info("Resolved dependency order: %s", install_order)
            return ResolverResult(
                success=True,
                install_order=install_order,
                errors=[],
                missing=[],
                conflicts=[]
            )

        except (RuntimeError, ValueError, TypeError, OSError) as exc:
            logger.error("Dependency resolution failed: %s", exc)
            errors.append(DependencyError(
                plugin_id="unknown",
                error_type="error",
                message=f"Resolution error: {exc}"
            ))
            return ResolverResult(
                success=False,
                install_order=[],
                errors=errors,
                missing=[],
                conflicts=[]
            )

    def _topological_sort(self, plugin_requirements: Dict[str, List[str]]) -> List[str]:
        """
        Topological sort using Kahn's algorithm.

        Args:
            plugin_requirements: Dict mapping plugin_id -> list of requirements

        Returns:
            Sorted list of plugin IDs (install order), or empty list if cycle detected
        """
        # Build dependency graph
        graph: Dict[str, Set[str]] = {pid: set() for pid in plugin_requirements}
        in_degree: Dict[str, int] = {pid: 0 for pid in plugin_requirements}

        for plugin_id, requirements in plugin_requirements.items():
            for req in requirements:
                dep_id, _, _ = self._parse_requirement(req)

                # Only consider dependencies within the set of plugins to install
                if dep_id in plugin_requirements:
                    graph[dep_id].add(plugin_id)
                    in_degree[plugin_id] += 1

        # Kahn's algorithm
        queue = [pid for pid in plugin_requirements if in_degree[pid] == 0]
        result = []

        while queue:
            current = queue.pop(0)
            result.append(current)

            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Check if all nodes were processed (no cycle)
        if len(result) != len(plugin_requirements):
            logger.error("Circular dependency detected")
            return []

        return result
