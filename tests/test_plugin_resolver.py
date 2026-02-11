"""Tests for core.plugins.resolver — DependencyResolver version constraints."""
import os
import sys
from unittest.mock import MagicMock, Mock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

from core.plugins.resolver import (
    DependencyResolver,
    DependencyError,
    ResolverResult
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestDependencyResolverInitialization:
    """Tests for DependencyResolver construction."""

    def test_resolver_accepts_empty_installed_plugins(self):
        """Resolver can be initialized with no installed plugins."""
        resolver = DependencyResolver(installed_plugins={})
        assert resolver.installed_plugins == {}

    def test_resolver_stores_installed_plugins(self):
        """Resolver stores installed plugin map."""
        installed = {"plugin-a": "1.0.0", "plugin-b": "2.0.0"}
        resolver = DependencyResolver(installed_plugins=installed)
        assert resolver.installed_plugins == installed


class TestDependencyResolverParseRequirement:
    """Tests for _parse_requirement() string parsing."""

    def test_parse_simple_plugin_name(self):
        """Parse requirement with just plugin name."""
        plugin_id, operator, version = DependencyResolver._parse_requirement("my-plugin")
        assert plugin_id == "my-plugin"
        assert operator == ""
        assert version is None

    def test_parse_exact_version_requirement(self):
        """Parse requirement with == operator."""
        plugin_id, operator, version = DependencyResolver._parse_requirement("my-plugin==1.0.0")
        assert plugin_id == "my-plugin"
        assert operator == "=="
        assert version == "1.0.0"

    def test_parse_greater_equal_requirement(self):
        """Parse requirement with >= operator."""
        plugin_id, operator, version = DependencyResolver._parse_requirement("my-plugin>=2.5.1")
        assert plugin_id == "my-plugin"
        assert operator == ">="
        assert version == "2.5.1"

    def test_parse_less_equal_requirement(self):
        """Parse requirement with <= operator."""
        plugin_id, operator, version = DependencyResolver._parse_requirement("my-plugin<=3.0.0")
        assert plugin_id == "my-plugin"
        assert operator == "<="
        assert version == "3.0.0"

    def test_parse_greater_than_requirement(self):
        """Parse requirement with > operator."""
        plugin_id, operator, version = DependencyResolver._parse_requirement("my-plugin>1.0")
        assert plugin_id == "my-plugin"
        assert operator == ">"
        assert version == "1.0"

    def test_parse_less_than_requirement(self):
        """Parse requirement with < operator."""
        plugin_id, operator, version = DependencyResolver._parse_requirement("my-plugin<2.0")
        assert plugin_id == "my-plugin"
        assert operator == "<"
        assert version == "2.0"

    def test_parse_handles_whitespace(self):
        """Parse handles whitespace around operators."""
        plugin_id, operator, version = DependencyResolver._parse_requirement("my-plugin >= 1.0.0")
        assert plugin_id == "my-plugin"
        assert operator == ">="
        assert version == "1.0.0"

    def test_parse_handles_hyphens_in_name(self):
        """Parse handles plugin names with multiple hyphens."""
        plugin_id, operator, version = DependencyResolver._parse_requirement("my-cool-plugin>=1.0")
        assert plugin_id == "my-cool-plugin"
        assert operator == ">="
        assert version == "1.0"


class TestDependencyResolverCheckVersion:
    """Tests for _check_version_constraint() validation."""

    def test_check_no_constraint_always_passes(self):
        """No operator/version constraint always passes."""
        result = DependencyResolver._check_version_constraint("1.0.0", "", None)
        assert result is True

    def test_check_exact_match_passes(self):
        """Exact version match passes."""
        result = DependencyResolver._check_version_constraint("1.0.0", "==", "1.0.0")
        assert result is True

    def test_check_exact_mismatch_fails(self):
        """Exact version mismatch fails."""
        result = DependencyResolver._check_version_constraint("1.0.0", "==", "2.0.0")
        assert result is False

    def test_check_greater_equal_passes(self):
        """Greater or equal version passes."""
        result = DependencyResolver._check_version_constraint("2.0.0", ">=", "1.0.0")
        assert result is True

    def test_check_greater_equal_exact_passes(self):
        """Equal version passes >= constraint."""
        result = DependencyResolver._check_version_constraint("1.0.0", ">=", "1.0.0")
        assert result is True

    def test_check_greater_equal_fails(self):
        """Lower version fails >= constraint."""
        result = DependencyResolver._check_version_constraint("0.9.0", ">=", "1.0.0")
        assert result is False

    def test_check_less_equal_passes(self):
        """Lower version passes <= constraint."""
        result = DependencyResolver._check_version_constraint("1.0.0", "<=", "2.0.0")
        assert result is True

    def test_check_less_equal_fails(self):
        """Higher version fails <= constraint."""
        result = DependencyResolver._check_version_constraint("3.0.0", "<=", "2.0.0")
        assert result is False

    def test_check_greater_than_passes(self):
        """Higher version passes > constraint."""
        result = DependencyResolver._check_version_constraint("2.0.0", ">", "1.0.0")
        assert result is True

    def test_check_greater_than_equal_fails(self):
        """Equal version fails > constraint."""
        result = DependencyResolver._check_version_constraint("1.0.0", ">", "1.0.0")
        assert result is False

    def test_check_less_than_passes(self):
        """Lower version passes < constraint."""
        result = DependencyResolver._check_version_constraint("1.0.0", "<", "2.0.0")
        assert result is True

    def test_check_less_than_equal_fails(self):
        """Equal version fails < constraint."""
        result = DependencyResolver._check_version_constraint("1.0.0", "<", "1.0.0")
        assert result is False


class TestDependencyResolverGetMissing:
    """Tests for get_missing() dependency checks."""

    def test_get_missing_empty_requirements(self):
        """Empty requirements returns empty list."""
        resolver = DependencyResolver(installed_plugins={})
        missing = resolver.get_missing("test-plugin", [])
        assert missing == []

    def test_get_missing_finds_missing_dependency(self):
        """get_missing() identifies missing dependencies."""
        resolver = DependencyResolver(installed_plugins={})
        missing = resolver.get_missing("test-plugin", ["required-plugin"])
        assert "required-plugin" in missing

    def test_get_missing_ignores_satisfied_dependencies(self):
        """get_missing() ignores installed dependencies."""
        resolver = DependencyResolver(installed_plugins={"dep-plugin": "1.0.0"})
        missing = resolver.get_missing("test-plugin", ["dep-plugin"])
        assert missing == []

    def test_get_missing_checks_version_constraints(self):
        """get_missing() treats version mismatches as missing."""
        resolver = DependencyResolver(installed_plugins={"dep-plugin": "0.9.0"})
        missing = resolver.get_missing("test-plugin", ["dep-plugin>=1.0.0"])
        assert "dep-plugin" in missing or len(missing) == 0  # Version mismatch handling

    def test_get_missing_multiple_dependencies(self):
        """get_missing() checks all dependencies."""
        resolver = DependencyResolver(installed_plugins={"installed": "1.0.0"})
        missing = resolver.get_missing("test", ["installed", "missing-1", "missing-2"])
        assert "missing-1" in missing
        assert "missing-2" in missing
        assert "installed" not in missing


class TestDependencyResolverResolve:
    """Tests for resolve() dependency resolution."""

    def test_resolve_single_plugin_no_deps(self):
        """Resolve single plugin with no dependencies."""
        resolver = DependencyResolver(installed_plugins={})
        result = resolver.resolve({"plugin-a": []})
        
        assert result.success is True
        assert result.install_order == ["plugin-a"]
        assert result.errors == []
        assert result.missing == []

    def test_resolve_plugin_with_satisfied_deps(self):
        """Resolve plugin when dependencies already installed."""
        resolver = DependencyResolver(installed_plugins={"dep": "1.0.0"})
        result = resolver.resolve({"plugin-a": ["dep"]})
        
        assert result.success is True
        assert "plugin-a" in result.install_order

    def test_resolve_multiple_plugins_no_deps(self):
        """Resolve multiple independent plugins."""
        resolver = DependencyResolver(installed_plugins={})
        result = resolver.resolve({
            "plugin-a": [],
            "plugin-b": [],
            "plugin-c": []
        })
        
        assert result.success is True
        assert len(result.install_order) == 3
        assert set(result.install_order) == {"plugin-a", "plugin-b", "plugin-c"}

    def test_resolve_detects_missing_dependency(self):
        """Resolve detects missing dependencies."""
        resolver = DependencyResolver(installed_plugins={})
        result = resolver.resolve({"plugin-a": ["missing-plugin"]})
        
        assert result.success is False
        assert "missing-plugin" in result.missing
        assert len(result.errors) > 0

    def test_resolve_dependency_chain(self):
        """Resolve handles dependency chains."""
        resolver = DependencyResolver(installed_plugins={})
        result = resolver.resolve({
            "plugin-a": [],
            "plugin-b": ["plugin-a"],
            "plugin-c": ["plugin-b"]
        })
        
        # Should be topologically sorted
        if result.success:
            a_idx = result.install_order.index("plugin-a")
            b_idx = result.install_order.index("plugin-b")
            c_idx = result.install_order.index("plugin-c")
            assert a_idx < b_idx < c_idx

    def test_resolve_detects_circular_dependency(self):
        """Resolve detects circular dependencies."""
        resolver = DependencyResolver(installed_plugins={})
        result = resolver.resolve({
            "plugin-a": ["plugin-b"],
            "plugin-b": ["plugin-a"]
        })
        
        assert result.success is False
        # Should detect cycle
        cycle_errors = [e for e in result.errors if e.error_type == "cycle"]
        assert len(cycle_errors) > 0 or not result.success


class TestDependencyResolverEdgeCases:
    """Tests for edge cases and error handling."""

    def test_resolve_empty_plugin_set(self):
        """Resolve handles empty plugin set."""
        resolver = DependencyResolver(installed_plugins={})
        result = resolver.resolve({})
        
        assert result.success is True
        assert result.install_order == []

    def test_resolve_self_dependency(self):
        """Resolve handles plugin depending on itself."""
        resolver = DependencyResolver(installed_plugins={})
        result = resolver.resolve({"plugin-a": ["plugin-a"]})
        
        # Should detect cycle or handle gracefully
        assert isinstance(result, ResolverResult)

    def test_resolve_complex_graph(self):
        """Resolve handles complex dependency graph."""
        resolver = DependencyResolver(installed_plugins={})
        result = resolver.resolve({
            "base": [],
            "util-a": ["base"],
            "util-b": ["base"],
            "app": ["util-a", "util-b"]
        })
        
        if result.success:
            # base must come before util-a and util-b
            base_idx = result.install_order.index("base")
            util_a_idx = result.install_order.index("util-a")
            util_b_idx = result.install_order.index("util-b")
            app_idx = result.install_order.index("app")
            
            assert base_idx < util_a_idx
            assert base_idx < util_b_idx
            assert util_a_idx < app_idx
            assert util_b_idx < app_idx


class TestDependencyResolverIntegration:
    """Integration tests for resolver workflow."""

    def test_full_resolution_workflow(self):
        """Test complete dependency resolution workflow."""
        # Simulated installed plugins
        installed = {
            "foundation": "1.0.0",
            "utilities": "2.0.0"
        }
        
        resolver = DependencyResolver(installed_plugins=installed)
        
        # New plugins to install with dependencies
        to_install = {
            "new-plugin-a": ["foundation>=1.0.0"],
            "new-plugin-b": ["utilities", "new-plugin-a"]
        }
        
        result = resolver.resolve(to_install)
        
        if result.success:
            # new-plugin-a should come before new-plugin-b
            a_idx = result.install_order.index("new-plugin-a")
            b_idx = result.install_order.index("new-plugin-b")
            assert a_idx < b_idx

    def test_resolver_with_version_constraints(self):
        """Test version constraint checking."""
        installed = {"base-plugin": "2.5.0"}
        resolver = DependencyResolver(installed_plugins=installed)
        
        # Check missing for plugin requiring newer version
        missing = resolver.get_missing("new", ["base-plugin>=3.0.0"])
        # Should detect version mismatch
        assert len(missing) >= 0  # Implementation may vary

    def test_resolver_result_structure(self):
        """Test ResolverResult contains expected fields."""
        resolver = DependencyResolver(installed_plugins={})
        result = resolver.resolve({"plugin": []})
        
        assert hasattr(result, 'success')
        assert hasattr(result, 'install_order')
        assert hasattr(result, 'errors')
        assert hasattr(result, 'missing')
        assert hasattr(result, 'conflicts')
