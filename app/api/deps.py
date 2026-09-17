"""Shared route dependencies: who is calling.

Identity always comes from the request headers, never from configuration -
the API is meant to be called straight from a frontend that holds the user's
session, and the server keeps no credentials of its own.
"""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header

from app.core.exceptions import AuthError
from app.core.jwt_claims import tenant_id


@dataclass(frozen=True)
class Caller:
    jwt: str
    tenant: str


def get_caller(
    authorization: Annotated[str | None, Header()] = None,
    tenant: Annotated[str | None, Header()] = None,
) -> Caller:
    """Identity of the calling user.

    Authorization: Bearer <leadrat-jwt>   required
    tenant: <tenant-id>                   optional, defaults to the token's
                                          custom:tenant_id claim
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthError("Missing Leadrat JWT. Send 'Authorization: Bearer <token>'.")

    jwt = authorization.split(" ", 1)[1].strip()
    if not jwt:
        raise AuthError("Empty Leadrat JWT in the Authorization header.")

    resolved_tenant = (tenant or "").strip() or tenant_id(jwt)
    if not resolved_tenant:
        raise AuthError(
            "Missing tenant. Send a 'tenant' header, or use a token carrying "
            "a custom:tenant_id claim."
        )

    return Caller(jwt=jwt, tenant=resolved_tenant)


CallerDep = Annotated[Caller, Depends(get_caller)]
