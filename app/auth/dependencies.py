"""Backward-compatible import shim for auth dependencies."""

from app.api.dependencies import (
    get_current_user,
    get_current_active_user,
    get_current_user_optional,
    require_admin,
    get_user_id,
    require_bearer_token,
)

__all__ = [
    "get_current_user",
    "get_current_active_user",
    "get_current_user_optional",
    "require_admin",
    "get_user_id",
    "require_bearer_token",
]
