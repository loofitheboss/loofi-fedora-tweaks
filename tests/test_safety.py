import unittest
from unittest.mock import patch
from utils.safety import SafetyManager
from utils.history import HistoryManager
import os
import subprocess


class TestSafety(unittest.TestCase):
    
    @patch('shutil.which')
    def test_check_snapshot_tool(self, mock_which):
        mock_which.return_value = "/usr/bin/timeshift"
        self.assertEqual(SafetyManager.check_snapshot_tool(), "timeshift")
        
        mock_which.side_effect = lambda x: "/usr/bin/snapper" if x == "snapper" else None
        self.assertEqual(SafetyManager.check_snapshot_tool(), "snapper")
        
    @patch('os.path.exists')
    @patch('subprocess.check_call')
    def test_check_dnf_lock(self, mock_check_call, mock_exists):
        # Case 1: PID file exists
        mock_exists.return_value = True
        self.assertTrue(SafetyManager.check_dnf_lock())
        
        # Case 2: PID file missing, but process running
        mock_exists.return_value = False
        mock_check_call.return_value = 0 # success (found)
        self.assertTrue(SafetyManager.check_dnf_lock())
        
        # Case 3: Neither
        mock_check_call.side_effect = subprocess.CalledProcessError(1, "pgrep")
        self.assertFalse(SafetyManager.check_dnf_lock())


class TestHistory(unittest.TestCase):
    def setUp(self):
        self.history_mgr = HistoryManager()
        self.history_mgr.HISTORY_FILE = "/tmp/test_loofi_history.json"
        if os.path.exists(self.history_mgr.HISTORY_FILE):
             os.remove(self.history_mgr.HISTORY_FILE)
             
    def tearDown(self):
        if os.path.exists(self.history_mgr.HISTORY_FILE):
             os.remove(self.history_mgr.HISTORY_FILE)
             
    def test_log_and_undo(self):
        self.history_mgr.log_change("Test Action", ["echo", "undo"])
        
        last = self.history_mgr.get_last_action()
        self.assertEqual(last["description"], "Test Action")
        self.assertEqual(last["undo_command"], ["echo", "undo"])
        
        # Undo
        with patch('subprocess.run') as mock_run:
            result = self.history_mgr.undo_last_action()
            self.assertTrue(result.success)
            mock_run.assert_called_with(["echo", "undo"], check=True, timeout=60)
            
        self.assertIsNone(self.history_mgr.get_last_action())

if __name__ == '__main__':
    unittest.main()
