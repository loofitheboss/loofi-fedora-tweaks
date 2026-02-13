"""
Tests for ReportExporter — v31.0 Smart UX
"""
import unittest
import sys
import os
import tempfile
from unittest.mock import patch, MagicMock

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.report_exporter import ReportExporter


class TestReportExporter(unittest.TestCase):
    """Tests for ReportExporter."""

    def _sample_info(self):
        """Return sample system info dict for testing."""
        return {
            "hostname": "test-host",
            "kernel": "6.8.0-100.fc40.x86_64",
            "fedora_version": "Fedora release 40 (Forty)",
            "cpu": "Intel Core i7-1365U",
            "ram": "16Gi total, 8Gi used",
            "disk_root": "45G/100G (45% used)",
            "uptime": "up 2 hours, 30 minutes",
            "battery": "85% (Discharging)",
            "architecture": "x86_64",
            "desktop": "GNOME",
            "report_date": "2026-02-13 12:00:00",
        }

    def test_export_markdown_structure(self):
        """Markdown export contains headers and table."""
        info = self._sample_info()
        md = ReportExporter.export_markdown(info)
        self.assertIn("# System Report", md)
        self.assertIn("## System Information", md)
        self.assertIn("| Property | Value |", md)
        self.assertIn("test-host", md)
        self.assertIn("Intel Core i7", md)

    def test_export_markdown_all_fields(self):
        """Markdown export includes all expected fields."""
        info = self._sample_info()
        md = ReportExporter.export_markdown(info)
        for key in ["Hostname", "Kernel", "CPU", "RAM", "Uptime", "Battery"]:
            self.assertIn(key, md)

    def test_export_markdown_missing_fields(self):
        """Markdown export handles missing fields gracefully."""
        info = {"hostname": "test", "report_date": "2026-01-01"}
        md = ReportExporter.export_markdown(info)
        self.assertIn("Unknown", md)  # Missing fields show Unknown

    def test_export_html_structure(self):
        """HTML export is a valid HTML document."""
        info = self._sample_info()
        html = ReportExporter.export_html(info)
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("<html", html)
        self.assertIn("</html>", html)
        self.assertIn("<table>", html)
        self.assertIn("test-host", html)

    def test_export_html_contains_style(self):
        """HTML export includes CSS styling."""
        info = self._sample_info()
        html = ReportExporter.export_html(info)
        self.assertIn("<style>", html)
        self.assertIn("font-family", html)

    def test_export_html_all_fields(self):
        """HTML export includes all expected fields."""
        info = self._sample_info()
        html = ReportExporter.export_html(info)
        for key in ["Hostname", "Kernel", "CPU", "RAM"]:
            self.assertIn(key, html)

    @patch('subprocess.getoutput')
    @patch('os.path.exists', return_value=False)
    @patch('os.environ.get', return_value="GNOME")
    def test_gather_system_info(self, mock_env, mock_exists, mock_getoutput):
        """gather_system_info returns dict with expected keys."""
        mock_getoutput.return_value = "test-value"
        info = ReportExporter.gather_system_info()
        self.assertIsInstance(info, dict)
        self.assertIn("hostname", info)
        self.assertIn("kernel", info)
        self.assertIn("cpu", info)
        self.assertIn("ram", info)
        self.assertIn("report_date", info)

    def test_save_report_markdown(self):
        """save_report writes Markdown file."""
        info = self._sample_info()
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
            path = f.name
        try:
            result = ReportExporter.save_report(path, "markdown", info)
            self.assertEqual(result, path)
            with open(path, "r") as f:
                content = f.read()
            self.assertIn("# System Report", content)
        finally:
            os.unlink(path)

    def test_save_report_html(self):
        """save_report writes HTML file."""
        info = self._sample_info()
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            path = f.name
        try:
            result = ReportExporter.save_report(path, "html", info)
            self.assertEqual(result, path)
            with open(path, "r") as f:
                content = f.read()
            self.assertIn("<!DOCTYPE html>", content)
        finally:
            os.unlink(path)

    @patch.object(ReportExporter, 'gather_system_info')
    def test_save_report_auto_gathers(self, mock_gather):
        """save_report gathers info if none provided."""
        mock_gather.return_value = self._sample_info()
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
            path = f.name
        try:
            ReportExporter.save_report(path, "markdown")
            mock_gather.assert_called_once()
        finally:
            os.unlink(path)


if __name__ == '__main__':
    unittest.main()
