"""Profile management API routes (v24.0)."""

from typing import Any, Dict

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from utils.auth import AuthManager
from utils.profiles import ProfileManager

router = APIRouter()


class ProfileApplyPayload(BaseModel):
    """Payload for profile application."""

    name: str = Field(..., description="Profile key")
    create_snapshot: bool = Field(True, description="Create snapshot before apply")


class ProfileImportPayload(BaseModel):
    """Payload for importing one profile."""

    profile: Dict[str, Any] = Field(..., description="Profile payload")
    overwrite: bool = Field(False, description="Overwrite custom profile if it exists")


class ProfileImportAllPayload(BaseModel):
    """Payload for importing profile bundles."""

    bundle: Dict[str, Any] = Field(..., description="Profile bundle payload")
    overwrite: bool = Field(False, description="Overwrite custom profiles if they exist")


@router.get("/profiles")
def list_profiles(_auth: str = Depends(AuthManager.verify_bearer_token)):
    """Return available profiles and currently active key."""
    return {
        "profiles": ProfileManager.list_profiles(),
        "active_profile": ProfileManager.get_active_profile(),
    }


@router.post("/profiles/apply", status_code=status.HTTP_200_OK)
def apply_profile(
    payload: ProfileApplyPayload,
    _auth: str = Depends(AuthManager.verify_bearer_token),
):
    """Apply a profile with optional snapshot hook."""
    result = ProfileManager.apply_profile(
        payload.name,
        create_snapshot=payload.create_snapshot,
    )
    return {
        "success": result.success,
        "message": result.message,
        "data": result.data,
    }


@router.get("/profiles/export-all")
def export_all_profiles(
    include_builtins: bool = False,
    _auth: str = Depends(AuthManager.verify_bearer_token),
):
    """Export all profiles as a bundle payload."""
    return ProfileManager.export_bundle_data(include_builtins=include_builtins)


@router.post("/profiles/import-all", status_code=status.HTTP_200_OK)
def import_all_profiles(
    payload: ProfileImportAllPayload,
    _auth: str = Depends(AuthManager.verify_bearer_token),
):
    """Import bundle payload."""
    result = ProfileManager.import_bundle_data(
        payload.bundle,
        overwrite=payload.overwrite,
    )
    return {
        "success": result.success,
        "message": result.message,
        "data": result.data,
    }


@router.get("/profiles/{name}/export")
def export_profile(
    name: str,
    _auth: str = Depends(AuthManager.verify_bearer_token),
):
    """Export one profile as payload."""
    payload = ProfileManager.export_profile_data(name)
    return payload or {
        "error": f"Profile '{name}' not found.",
    }


@router.post("/profiles/import", status_code=status.HTTP_200_OK)
def import_profile(
    payload: ProfileImportPayload,
    _auth: str = Depends(AuthManager.verify_bearer_token),
):
    """Import one profile payload."""
    result = ProfileManager.import_profile_data(
        payload.profile,
        overwrite=payload.overwrite,
    )
    return {
        "success": result.success,
        "message": result.message,
        "data": result.data,
    }
