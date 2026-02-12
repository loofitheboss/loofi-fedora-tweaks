"""Authentication utilities for Loofi Web API."""

import secrets
from pathlib import Path
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt

from utils.config_manager import ConfigManager


class AuthManager:
    """Manage API auth credentials and JWT verification."""

    _ALGORITHM = "HS256"
    _CONFIG_KEY = "api_auth"
    _CONFIG_FILE = "api_auth.json"
    _TOKEN_LIFETIME_SECONDS = 3600

    security = HTTPBearer(auto_error=False)

    @classmethod
    def _auth_path(cls) -> Path:
        return ConfigManager.CONFIG_DIR / cls._CONFIG_FILE

    @classmethod
    def _ensure_secret(cls, data: dict) -> dict:
        if not data.get("jwt_secret"):
            data["jwt_secret"] = secrets.token_hex(32)
        return data

    @classmethod
    def _load_auth_data(cls) -> dict:
        ConfigManager.ensure_dirs()
        config = ConfigManager.load_config() or {}
        return cls._ensure_secret(config.get(cls._CONFIG_KEY, {}))

    @classmethod
    def _save_auth_data(cls, data: dict) -> None:
        ConfigManager.ensure_dirs()
        config = ConfigManager.load_config() or {}
        config[cls._CONFIG_KEY] = data
        ConfigManager.save_config(config)
        try:
            cls._auth_path().write_text("1")
        except Exception:
            pass

    @classmethod
    def _hash_key(cls, api_key: str) -> str:
        return bcrypt.hashpw(api_key.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")  # type: ignore[return-value]

    @classmethod
    def generate_api_key(cls) -> str:
        """Generate and store a new API key."""
        api_key = secrets.token_urlsafe(32)
        data = cls._load_auth_data()
        data["api_key_hash"] = cls._hash_key(api_key)
        data = cls._ensure_secret(data)
        cls._save_auth_data(data)
        return api_key

    @classmethod
    def issue_token(cls, api_key: str) -> str:
        """Issue a JWT for a valid API key."""
        data = cls._load_auth_data()
        stored_hash = data.get("api_key_hash")
        if not stored_hash or not bcrypt.checkpw(api_key.encode("utf-8"), stored_hash.encode("utf-8")):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
        payload = {"sub": "loofi-api", "exp": int(__import__("time").time()) + cls._TOKEN_LIFETIME_SECONDS}
        return str(jwt.encode(payload, data["jwt_secret"], algorithm=cls._ALGORITHM))

    @classmethod
    def verify_token(cls, token: str) -> None:
        data = cls._load_auth_data()
        try:
            jwt.decode(token, data["jwt_secret"], algorithms=[cls._ALGORITHM])
        except Exception:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    @classmethod
    def verify_bearer_token(
        cls,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    ) -> str:
        if not credentials or credentials.scheme.lower() != "bearer":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
        cls.verify_token(credentials.credentials)
        return str(credentials.credentials)
