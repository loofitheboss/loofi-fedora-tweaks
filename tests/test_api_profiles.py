"""Tests for profile API routes (v24.0)."""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

import pytest

try:
    from fastapi.testclient import TestClient
    _HAS_FASTAPI = True
except ImportError:
    _HAS_FASTAPI = False

pytestmark = pytest.mark.skipif(not _HAS_FASTAPI, reason="fastapi not installed")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

if _HAS_FASTAPI:
    from utils.api_server import APIServer
    from utils.auth import AuthManager
    from utils.containers import Result
else:
    # Dummy so @patch return_value=Result(...) doesn't crash at collection
    class Result:  # type: ignore[no-redef]
        def __init__(self, success=True, message="", data=None):
            self.success = success
            self.message = message
            self.data = data or {}


class TestAPIProfiles(unittest.TestCase):
    """Profile endpoint coverage with auth override."""

    @classmethod
    def setUpClass(cls):
        server = APIServer()
        server.app.dependency_overrides[AuthManager.verify_bearer_token] = lambda: "test-token"
        cls.client = TestClient(server.app)

    @patch("api.routes.profiles.ProfileManager.get_active_profile", return_value="gaming")
    @patch("api.routes.profiles.ProfileManager.list_profiles", return_value=[{"key": "gaming", "builtin": True}])
    def test_profiles_list(self, mock_list, mock_active):
        resp = self.client.get("/api/profiles")
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["active_profile"], "gaming")
        self.assertEqual(payload["profiles"][0]["key"], "gaming")

    @patch("api.routes.profiles.ProfileManager.apply_profile", return_value=Result(True, "ok", {"warnings": []}))
    def test_profiles_apply(self, mock_apply):
        resp = self.client.post("/api/profiles/apply", json={"name": "gaming", "create_snapshot": False})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["success"])

    @patch("api.routes.profiles.ProfileManager.export_profile_data", return_value={})
    def test_profile_export_single_not_found(self, mock_export):
        resp = self.client.get("/api/profiles/unknown/export")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("error", resp.json())

    def test_profile_import_single_validation_error(self):
        resp = self.client.post("/api/profiles/import", json={"overwrite": False})
        self.assertEqual(resp.status_code, 422)

    @patch("api.routes.profiles.ProfileManager.import_profile_data", return_value=Result(True, "imported", {"key": "one"}))
    def test_profile_import_single_success(self, mock_import):
        resp = self.client.post(
            "/api/profiles/import",
            json={"profile": {"key": "one", "name": "One", "settings": {}}, "overwrite": False},
        )
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["data"]["key"], "one")

    @patch("api.routes.profiles.ProfileManager.export_bundle_data", return_value={"kind": "profile_bundle", "profiles": []})
    def test_profile_export_all(self, mock_export_all):
        resp = self.client.get("/api/profiles/export-all?include_builtins=true")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["kind"], "profile_bundle")

    @patch("api.routes.profiles.ProfileManager.import_bundle_data", return_value=Result(False, "with errors", {"errors": [{"key": "x"}]}))
    def test_profile_import_all_overwrite(self, mock_import_all):
        resp = self.client.post(
            "/api/profiles/import-all",
            json={
                "bundle": {"schema_version": 1, "profiles": [{"key": "x", "name": "X", "settings": {}}]},
                "overwrite": True,
            },
        )
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertFalse(payload["success"])
        self.assertEqual(payload["data"]["errors"][0]["key"], "x")


if __name__ == "__main__":
    unittest.main()
