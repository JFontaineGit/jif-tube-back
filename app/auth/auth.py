"""Backward-compatible import shim for the authentication router."""

from app.api.auth import router as auth_router

__all__ = ["auth_router"]
