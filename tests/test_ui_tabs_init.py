"""UI Tab Instantiation Tests — pytest style with autouse qapp fixture."""
import os
import sys
from unittest.mock import patch, MagicMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

_tab_refs = []


def _mock_perf():
    m = MagicMock()
    m.get_cpu_usage.return_value = 10.0
    m.get_memory_usage.return_value = {"percent": 40.0, "used_gb": 4.0, "total_gb": 16.0}
    m.get_disk_usage.return_value = {"percent": 50.0, "used_gb": 100, "total_gb": 200}
    m.get_swap_usage.return_value = {"percent": 10.0}
    m.get_cpu_temp.return_value = 45.0
    m.get_gpu_info.return_value = {"name": "Test GPU", "usage": 0}
    m.get_network_stats.return_value = {"rx_rate": 0, "tx_rate": 0}
    return m


@patch("ui.monitor_tab.ProcessManager")
@patch("ui.monitor_tab.PerformanceCollector")
def test_monitor_tab_init(mock_perf_cls, mock_proc_cls):
    mock_perf_cls.return_value = _mock_perf()
    mock_proc_cls.return_value = MagicMock()
    mock_proc_cls.return_value.get_processes.return_value = []
    from ui.monitor_tab import MonitorTab
    tab = MonitorTab()
    _tab_refs.append(tab)
    assert tab is not None


@patch("subprocess.run", return_value=MagicMock(returncode=0, stdout=""))
@patch("subprocess.check_output", return_value="")
def test_network_tab_init(mock_co, mock_run):
    from ui.network_tab import NetworkTab
    tab = NetworkTab()
    _tab_refs.append(tab)
    assert tab is not None


@patch("subprocess.run", return_value=MagicMock(returncode=0, stdout=""))
@patch("subprocess.check_output", return_value="")
@patch("shutil.which", return_value=None)
def test_development_tab_init(mock_which, mock_co, mock_run):
    from ui.development_tab import DevelopmentTab
    tab = DevelopmentTab()
    _tab_refs.append(tab)
    assert tab is not None


@patch("subprocess.run", return_value=MagicMock(returncode=0, stdout=""))
@patch("subprocess.check_output", return_value="")
def test_dashboard_tab_init(mock_co, mock_run):
    from ui.dashboard_tab import DashboardTab
    tab = DashboardTab()
    _tab_refs.append(tab)
    assert tab is not None


@patch("subprocess.run", return_value=MagicMock(returncode=0, stdout=""))
@patch("subprocess.check_output", return_value="")
@patch("shutil.which", return_value=None)
def test_virtualization_tab_init(mock_which, mock_co, mock_run):
    from ui.virtualization_tab import VirtualizationTab
    tab = VirtualizationTab()
    _tab_refs.append(tab)
    assert tab is not None


@patch("subprocess.run", return_value=MagicMock(returncode=0, stdout=""))
@patch("subprocess.check_output", return_value="")
@patch("shutil.which", return_value=None)
def test_hardware_tab_init(mock_which, mock_co, mock_run):
    from ui.hardware_tab import HardwareTab
    tab = HardwareTab()
    _tab_refs.append(tab)
    assert tab is not None


@patch("subprocess.run", return_value=MagicMock(returncode=0, stdout=""))
@patch("subprocess.check_output", return_value="")
@patch("shutil.which", return_value=None)
def test_ai_enhanced_tab_init(mock_which, mock_co, mock_run):
    from ui.ai_enhanced_tab import AIEnhancedTab
    tab = AIEnhancedTab()
    _tab_refs.append(tab)
    assert tab is not None


@patch("subprocess.run", return_value=MagicMock(returncode=0, stdout=""))
@patch("subprocess.check_output", return_value="")
def test_automation_tab_init(mock_co, mock_run):
    from ui.automation_tab import AutomationTab
    tab = AutomationTab()
    _tab_refs.append(tab)
    assert tab is not None


@patch("subprocess.run", return_value=MagicMock(returncode=0, stdout=""))
@patch("subprocess.check_output", return_value="")
@patch("shutil.which", return_value="/usr/bin/dnf")
def test_maintenance_tab_init(mock_which, mock_co, mock_run):
    from ui.maintenance_tab import MaintenanceTab
    tab = MaintenanceTab()
    _tab_refs.append(tab)
    assert tab is not None


@patch("subprocess.run", return_value=MagicMock(returncode=0, stdout=""))
@patch("subprocess.check_output", return_value="")
def test_mesh_tab_init(mock_co, mock_run):
    from ui.mesh_tab import MeshTab
    tab = MeshTab()
    _tab_refs.append(tab)
    assert tab is not None


@patch("subprocess.run", return_value=MagicMock(returncode=0, stdout=""))
@patch("subprocess.check_output", return_value="")
def test_teleport_tab_init(mock_co, mock_run):
    from ui.teleport_tab import TeleportTab
    tab = TeleportTab()
    _tab_refs.append(tab)
    assert tab is not None


@patch("subprocess.run", return_value=MagicMock(returncode=0, stdout=""))
@patch("subprocess.check_output", return_value="")
@patch("shutil.which", return_value="/usr/bin/dnf")
def test_software_tab_init(mock_which, mock_co, mock_run):
    from ui.software_tab import SoftwareTab
    tab = SoftwareTab()
    _tab_refs.append(tab)
    assert tab is not None


@patch("subprocess.run", return_value=MagicMock(returncode=0, stdout=""))
@patch("subprocess.check_output", return_value="")
@patch("shutil.which", return_value=None)
def test_gaming_tab_init(mock_which, mock_co, mock_run):
    from ui.gaming_tab import GamingTab
    tab = GamingTab()
    _tab_refs.append(tab)
    assert tab is not None


@patch("subprocess.run", return_value=MagicMock(returncode=0, stdout=""))
@patch("subprocess.check_output", return_value="")
def test_desktop_tab_init(mock_co, mock_run):
    from ui.desktop_tab import DesktopTab
    tab = DesktopTab()
    _tab_refs.append(tab)
    assert tab is not None


@patch("subprocess.run", return_value=MagicMock(returncode=0, stdout=""))
@patch("subprocess.check_output", return_value="")
@patch("shutil.which", return_value=None)
def test_security_tab_init(mock_which, mock_co, mock_run):
    from ui.security_tab import SecurityTab
    tab = SecurityTab()
    _tab_refs.append(tab)
    assert tab is not None


@patch("subprocess.run", return_value=MagicMock(returncode=0, stdout=""))
@patch("subprocess.check_output", return_value="")
def test_community_tab_init(mock_co, mock_run):
    from ui.community_tab import CommunityTab
    tab = CommunityTab()
    _tab_refs.append(tab)
    assert tab is not None


@patch("subprocess.run", return_value=MagicMock(returncode=0, stdout=""))
@patch("subprocess.check_output", return_value="")
def test_diagnostics_tab_init(mock_co, mock_run):
    from ui.diagnostics_tab import DiagnosticsTab
    tab = DiagnosticsTab()
    _tab_refs.append(tab)
    assert tab is not None
