"""Request-scoped caller identity.

The Leadrat JWT and tenant belong to the caller, not to the process, so they
travel in ContextVars: the API sets them once per request and the CRM client
reads them deep down the stack without every layer passing them along.
"""

from collections.abc import Iterator
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


def iter_as_caller(
    jwt: str | None, tenant: str | None, make_iterator
) -> Iterator:
    """Run a lazy iterator with the caller's identity set on every step.

    A `with use_caller(...)` block cannot wrap a generator that is consumed by
    Starlette's `iterate_in_threadpool`: each `next()` runs in its own copy of
    the context, so the ContextVar set on one step is gone on the next and the
    final `reset()` raises "was created in a different Context". Setting and
    resetting inside each step keeps set and reset in the same context, and
    keeps the identity visible to whatever the step calls.
    """
    with use_caller(jwt, tenant):
        iterator = iter(make_iterator())
    while True:
        with use_caller(jwt, tenant):
            try:
                item = next(iterator)
            except StopIteration:
                return
        yield item
