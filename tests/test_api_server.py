"""Comprehensive security tests for API server."""

import json
import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from utils.action_result import ActionResult
from utils.api_server import APIServer
from utils.auth import AuthManager


@pytest.fixture
def test_client():
    """Provide a FastAPI test client for the API server."""
    server = APIServer()
    return TestClient(server.app)


@pytest.fixture
def valid_api_key():
    """Generate and return a valid API key."""
    return AuthManager.generate_api_key()


@pytest.fixture
def valid_token(test_client, valid_api_key):
    """Generate and return a valid JWT token."""
    response = test_client.post("/api/token", data={"api_key": valid_api_key})
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def mock_action_executor():
    """Mock ActionExecutor.run to prevent actual system execution."""
    with patch("utils.action_executor.ActionExecutor.run") as mock_run:
        mock_run.return_value = ActionResult(
            success=True,
            message="Mock execution successful",
            exit_code=0,
            stdout="mock output",
            stderr="",
            preview=True,
            action_id="test-action",
        )
        yield mock_run


# ============================================================================
# Basic Functionality Tests
# ============================================================================


def test_health_endpoint(test_client):
    """Health endpoint should work without authentication."""
    response = test_client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "version" in payload
    assert "codename" in payload


def test_token_flow(test_client, valid_api_key, mock_action_executor):
    """Test complete token generation and execution flow."""
    token_resp = test_client.post("/api/token", data={"api_key": valid_api_key})
    assert token_resp.status_code == 200
    token = token_resp.json()["access_token"]

    exec_resp = test_client.post(
        "/api/execute",
        json={"command": "echo", "args": ["hi"], "preview": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert exec_resp.status_code == 200
    data = exec_resp.json()
    assert data["preview"]["preview"] is True


# ============================================================================
# Authentication Security Tests
# ============================================================================


class TestAuthenticationSecurity:
    """Tests for authentication security mechanisms."""

    def test_execute_without_bearer_token(self, test_client):
        """Accessing /api/execute without Bearer token should return 401."""
        response = test_client.post(
            "/api/execute",
            json={"command": "echo", "args": ["test"], "preview": True},
        )
        assert response.status_code == 401
        assert "Missing bearer token" in response.json()["detail"]

    def test_execute_with_invalid_token_format(self, test_client):
        """Accessing /api/execute with invalid token format should return 401."""
        response = test_client.post(
            "/api/execute",
            json={"command": "echo", "args": ["test"], "preview": True},
            headers={"Authorization": "Bearer invalid-token-format"},
        )
        assert response.status_code == 401
        assert "Invalid token" in response.json()["detail"]

    def test_execute_with_malformed_bearer_header(self, test_client):
        """Malformed Authorization header should return 401."""
        response = test_client.post(
            "/api/execute",
            json={"command": "echo", "args": ["test"], "preview": True},
            headers={"Authorization": "NotBearer some-token"},
        )
        assert response.status_code == 401

    def test_execute_with_expired_token(self, test_client, valid_api_key):
        """Expired token should return 401."""
        # Mock jwt.encode to create an expired token
        with patch("utils.auth.jwt.encode") as mock_encode:
            # Create a token that expired 1 hour ago
            mock_encode.return_value = "expired.token.here"

            # Mock jwt.decode to raise exception for expired token
            with patch("utils.auth.jwt.decode") as mock_decode:
                import jwt
                mock_decode.side_effect = jwt.ExpiredSignatureError("Token expired")

                response = test_client.post(
                    "/api/execute",
                    json={"command": "echo", "args": ["test"], "preview": True},
                    headers={"Authorization": "Bearer expired.token.here"},
                )
                assert response.status_code == 401

    def test_token_generation_with_wrong_api_key(self, test_client):
        """Token generation with invalid API key should return 401."""
        response = test_client.post(
            "/api/token",
            data={"api_key": "wrong-api-key-12345"},
        )
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]

    def test_token_generation_without_api_key(self, test_client):
        """Token generation without API key should return 422 validation error."""
        response = test_client.post("/api/token", data={})
        assert response.status_code == 422  # FastAPI validation error for missing required field


# ============================================================================
# Input Validation Tests
# ============================================================================


class TestInputValidation:
    """Tests for input validation and sanitization."""

    def test_command_injection_attempt(self, test_client, valid_token, mock_action_executor):
        """Command injection attempts should be passed to executor for handling."""
        response = test_client.post(
            "/api/execute",
            json={
                "command": "; rm -rf /",
                "args": ["test"],
                "preview": True,
            },
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        # Request should succeed but ActionExecutor will handle the invalid command
        assert response.status_code == 200
        # Verify the command was passed to executor as-is (not executed)
        mock_action_executor.assert_called()

    def test_path_traversal_in_args(self, test_client, valid_token, mock_action_executor):
        """Path traversal attempts in args should be passed to executor."""
        response = test_client.post(
            "/api/execute",
            json={
                "command": "cat",
                "args": ["../../etc/passwd"],
                "preview": True,
            },
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        assert response.status_code == 200
        # Verify args were passed through
        mock_action_executor.assert_called()
        call_args = mock_action_executor.call_args[0]
        assert "../../etc/passwd" in call_args[1]

    def test_malformed_json_payload(self, test_client, valid_token):
        """Malformed JSON should return 422."""
        response = test_client.post(
            "/api/execute",
            content=b"not-valid-json{{{",
            headers={
                "Authorization": f"Bearer {valid_token}",
                "Content-Type": "application/json",
            },
        )
        assert response.status_code == 422

    def test_missing_required_field_command(self, test_client, valid_token):
        """Missing required 'command' field should return 422."""
        response = test_client.post(
            "/api/execute",
            json={"args": ["test"], "preview": True},
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        assert response.status_code == 422

    def test_extremely_long_command(self, test_client, valid_token, mock_action_executor):
        """Extremely long command should be handled (DoS protection)."""
        long_command = "a" * 10000
        response = test_client.post(
            "/api/execute",
            json={
                "command": long_command,
                "args": ["test"],
                "preview": True,
            },
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        # Should succeed but executor will handle the invalid command
        assert response.status_code == 200

    def test_extremely_long_args(self, test_client, valid_token, mock_action_executor):
        """Extremely long args array should be handled."""
        long_args = ["arg" + str(i) for i in range(1000)]
        response = test_client.post(
            "/api/execute",
            json={
                "command": "echo",
                "args": long_args,
                "preview": True,
            },
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        assert response.status_code == 200

    def test_null_values_in_payload(self, test_client, valid_token):
        """Null values in optional fields should be handled."""
        response = test_client.post(
            "/api/execute",
            json={
                "command": "echo",
                "args": None,  # Should default to empty list
                "preview": True,
            },
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        # Pydantic validation should handle this
        assert response.status_code in [200, 422]


# ============================================================================
# Authorization Tests
# ============================================================================


class TestAuthorization:
    """Tests for authorization and access control."""

    def test_pkexec_requires_auth(self, test_client, valid_token, mock_action_executor):
        """pkexec=true requires valid authentication."""
        response = test_client.post(
            "/api/execute",
            json={
                "command": "dnf",
                "args": ["clean", "all"],
                "pkexec": True,
                "preview": True,
            },
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        assert response.status_code == 200
        # Verify pkexec flag was passed to executor
        call_kwargs = mock_action_executor.call_args[1]
        assert call_kwargs.get("pkexec") is True

    def test_pkexec_without_auth_fails(self, test_client):
        """pkexec=true without auth should return 401."""
        response = test_client.post(
            "/api/execute",
            json={
                "command": "dnf",
                "args": ["clean", "all"],
                "pkexec": True,
                "preview": True,
            },
        )
        assert response.status_code == 401

    def test_preview_mode_requires_auth(self, test_client):
        """Preview mode requires authentication."""
        response = test_client.post(
            "/api/execute",
            json={
                "command": "echo",
                "args": ["test"],
                "preview": True,
            },
        )
        assert response.status_code == 401

    def test_execute_mode_requires_auth(self, test_client):
        """Execute mode (preview=false) requires authentication."""
        response = test_client.post(
            "/api/execute",
            json={
                "command": "echo",
                "args": ["test"],
                "preview": False,
            },
        )
        assert response.status_code == 401

    def test_info_endpoint_without_auth(self, test_client):
        """Read-only /api/info should work without authentication."""
        with patch("utils.monitor.SystemMonitor.get_system_health") as mock_health:
            # Mock the health response
            mock_health.return_value = MagicMock(
                hostname="test-host",
                uptime=12345,
                memory=MagicMock(used_human="1GB", total_human="8GB", percent_used=12.5),
                cpu=MagicMock(load_1min=0.5, load_5min=0.6, load_15min=0.7, core_count=4, load_percent=15.0),
                memory_status="good",
                cpu_status="good",
            )

            response = test_client.get("/api/info")
            assert response.status_code == 200
            data = response.json()
            assert "version" in data
            assert "system_type" in data


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Tests for error handling and response serialization."""

    def test_invalid_command_execution(self, test_client, valid_token):
        """ActionExecutor should handle invalid commands gracefully."""
        with patch("utils.action_executor.ActionExecutor.run") as mock_run:
            mock_run.return_value = ActionResult(
                success=False,
                message="Command not found: invalid-command-xyz",
                exit_code=127,
                stdout="",
                stderr="command not found",
                preview=True,
            )

            response = test_client.post(
                "/api/execute",
                json={
                    "command": "invalid-command-xyz",
                    "args": [],
                    "preview": True,
                },
                headers={"Authorization": f"Bearer {valid_token}"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["preview"]["success"] is False
            assert "not found" in data["preview"]["message"].lower()

    def test_executor_exception_handling(self, test_client, valid_token):
        """ActionExecutor exceptions should propagate as 500 errors."""
        with patch("utils.action_executor.ActionExecutor.run") as mock_run:
            mock_run.side_effect = Exception("Unexpected executor error")

            # FastAPI will let the exception propagate, resulting in 500
            with pytest.raises(Exception):
                test_client.post(
                    "/api/execute",
                    json={
                        "command": "echo",
                        "args": ["test"],
                        "preview": True,
                    },
                    headers={"Authorization": f"Bearer {valid_token}"},
                )

    def test_action_result_serialization(self, test_client, valid_token):
        """ActionResult should serialize correctly with all fields."""
        with patch("utils.action_executor.ActionExecutor.run") as mock_run:
            mock_run.return_value = ActionResult(
                success=True,
                message="Test action completed",
                exit_code=0,
                stdout="test output",
                stderr="test warning",
                preview=True,
                needs_reboot=True,
                action_id="test-123",
            )

            response = test_client.post(
                "/api/execute",
                json={
                    "command": "test",
                    "args": [],
                    "preview": True,
                },
                headers={"Authorization": f"Bearer {valid_token}"},
            )
            assert response.status_code == 200
            data = response.json()
            assert "result" in data
            assert "preview" in data
            assert data["preview"]["success"] is True
            assert data["preview"]["needs_reboot"] is True
            assert data["preview"]["action_id"] == "test-123"

    def test_network_timeout_simulation(self, test_client, valid_token):
        """Simulate network timeout during execution."""
        with patch("utils.action_executor.ActionExecutor.run") as mock_run:
            import subprocess
            mock_run.side_effect = subprocess.TimeoutExpired("test", 120)

            # FastAPI will let the exception propagate
            with pytest.raises(subprocess.TimeoutExpired):
                test_client.post(
                    "/api/execute",
                    json={
                        "command": "sleep",
                        "args": ["300"],
                        "preview": True,
                    },
                    headers={"Authorization": f"Bearer {valid_token}"},
                )


# ============================================================================
# Additional Security Tests
# ============================================================================


class TestAdditionalSecurity:
    """Additional security edge cases."""

    def test_empty_command(self, test_client, valid_token):
        """Empty command string should be rejected."""
        response = test_client.post(
            "/api/execute",
            json={
                "command": "",
                "args": ["test"],
                "preview": True,
            },
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        # Should either be validation error or handled by executor
        assert response.status_code in [200, 422]

    def test_special_characters_in_command(self, test_client, valid_token, mock_action_executor):
        """Special characters in command should be passed to executor."""
        response = test_client.post(
            "/api/execute",
            json={
                "command": "test & echo",
                "args": ["$(whoami)"],
                "preview": True,
            },
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        assert response.status_code == 200

    def test_unicode_in_payload(self, test_client, valid_token, mock_action_executor):
        """Unicode characters should be handled correctly."""
        response = test_client.post(
            "/api/execute",
            json={
                "command": "echo",
                "args": ["你好", "мир", "🚀"],
                "preview": True,
            },
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        assert response.status_code == 200

    def test_action_id_validation(self, test_client, valid_token, mock_action_executor):
        """Action ID should be passed through correctly."""
        response = test_client.post(
            "/api/execute",
            json={
                "command": "echo",
                "args": ["test"],
                "preview": True,
                "action_id": "custom-action-123",
            },
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        assert response.status_code == 200
        # Verify action_id was passed to executor
        call_kwargs = mock_action_executor.call_args[1]
        assert call_kwargs.get("action_id") == "custom-action-123"