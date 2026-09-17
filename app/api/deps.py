"""Shared route dependencies."""

from typing import Annotated

from fastapi import Depends, Header

from app.core.config import settings
from app.core.exceptions import AuthError


def get_jwt_token(
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    """Leadrat JWT of the calling user, taken from `Authorization: Bearer <token>`.

    Falls back to LEADRAT_JWT in .env for local development. With the mock CRM
    no token is needed at all.
    """
    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    if settings.leadrat_jwt:
        return settings.leadrat_jwt
    if settings.use_mock_crm:
        return ""
    raise AuthError("Missing Leadrat JWT. Send 'Authorization: Bearer <token>'.")


JWTToken = Annotated[str, Depends(get_jwt_token)]
