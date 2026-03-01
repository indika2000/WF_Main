import os
from typing import Any

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security = HTTPBearer(auto_error=False)


def verify_jwt(token: str, secret: str | None = None) -> dict[str, Any]:
    """Decode and verify an HS256 JWT. Returns the decoded payload."""
    secret = secret or os.environ.get("JWT_SECRET", "")
    try:
        return jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def verify_api_key(request: Request) -> bool:
    """Check X-Api-Key header against the expected internal API key."""
    expected = os.environ.get("INTERNAL_API_KEY", "")
    actual = request.headers.get("X-Api-Key", "")
    if not actual or actual != expected:
        return False
    return True


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict[str, Any]:
    """FastAPI dependency: extract and verify JWT or API key.

    Returns a user dict with uid, email, role, permissions.
    Service-to-service calls with API key get a service identity.
    """
    # Check API key first (service-to-service)
    if verify_api_key(request):
        return {
            "uid": "service",
            "email": "service@internal",
            "role": "service",
            "permissions": {},
        }

    # Check Bearer token
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Authorization header required",
        )

    payload = verify_jwt(credentials.credentials)
    return {
        "uid": payload.get("uid", ""),
        "email": payload.get("email", ""),
        "role": payload.get("role", "user"),
        "permissions": payload.get("permissions", {}),
    }


def require_role(role: str):
    """FastAPI dependency factory: require the current user to have a specific role."""

    async def _check_role(
        current_user: dict[str, Any] = Depends(get_current_user),
    ) -> dict[str, Any]:
        user_role = current_user.get("role", "user")
        if user_role != role and user_role != "service":
            raise HTTPException(
                status_code=403,
                detail=f"Role '{role}' required",
            )
        return current_user

    return _check_role
