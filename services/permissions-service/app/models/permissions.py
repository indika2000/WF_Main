from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

DEFAULT_PERMISSIONS: dict[str, bool] = {
    "ad_free": False,
    "premium_features": False,
    "ai_text_generation": False,
    "ai_image_generation": False,
    "advanced_search": False,
    "unlimited_storage": False,
    "priority_support": False,
}


class UserPermissions(BaseModel):
    """User permission flags and role."""

    user_id: str
    email: str | None = None
    role: str = "user"  # user | admin | moderator
    is_premium: bool = False
    is_admin: bool = False
    permissions: dict[str, bool] = Field(
        default_factory=lambda: DEFAULT_PERMISSIONS.copy()
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PermissionsCreate(BaseModel):
    """Body for creating a new user's permissions."""

    email: str | None = None


class PermissionsUpdate(BaseModel):
    """Partial update to permission flags or role."""

    role: str | None = None
    is_premium: bool | None = None
    is_admin: bool | None = None
    permissions: dict[str, bool] | None = None


class PermissionCheckResponse(BaseModel):
    """Response for a single permission check."""

    user_id: str
    permission: str
    allowed: bool
