"""Request-scoped caller identity.

The Leadrat JWT and tenant belong to the caller, not to the process, so they
travel in ContextVars: the API sets them once per request and the CRM client
reads them deep down the stack without every layer passing them along.
"""

from contextlib import contextmanager
from contextvars import ContextVar

_jwt: ContextVar[str | None] = ContextVar("leadrat_jwt", default=None)
_tenant: ContextVar[str | None] = ContextVar("leadrat_tenant", default=None)


def get_jwt() -> str | None:
    return _jwt.get()


def get_tenant() -> str | None:
    return _tenant.get()


@contextmanager
def use_caller(jwt: str | None, tenant: str | None = None):
    jwt_token = _jwt.set(jwt)
    tenant_token = _tenant.set(tenant)
    try:
        yield
    finally:
        _jwt.reset(jwt_token)
        _tenant.reset(tenant_token)
