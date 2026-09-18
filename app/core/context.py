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

# Whatever this caller's request has already looked up: their permissions, the
# tenant's settings. It travels with the identity because that is exactly how
# long it is valid for - a different caller must never see it.
#
# The dict is mutated in place, never re-set. A streaming turn runs each step
# in its own copy of the context, so a `set()` inside a step is discarded when
# that step ends; writing into a dict the caller's scope already holds is what
# makes a lookup in step one still be there in step four.
_request_cache: ContextVar[dict | None] = ContextVar("leadrat_request_cache", default=None)


def get_jwt() -> str | None:
    return _jwt.get()


def get_tenant() -> str | None:
    return _tenant.get()


def request_cache() -> dict:
    """This request's scratch space; empty and inert outside a caller scope."""
    cache = _request_cache.get()
    return cache if cache is not None else {}


@contextmanager
def use_caller(jwt: str | None, tenant: str | None = None, cache: dict | None = None):
    """Run a block as this caller.

    `cache` is passed in by a streaming turn, which needs one scratch space
    shared by every step rather than a fresh one per step.
    """
    jwt_token = _jwt.set(jwt)
    tenant_token = _tenant.set(tenant)
    cache_token = _request_cache.set({} if cache is None else cache)
    try:
        yield
    finally:
        _jwt.reset(jwt_token)
        _tenant.reset(tenant_token)
        _request_cache.reset(cache_token)


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
    cache: dict = {}
    with use_caller(jwt, tenant, cache):
        iterator = iter(make_iterator())
    while True:
        with use_caller(jwt, tenant, cache):
            try:
                item = next(iterator)
            except StopIteration:
                return
        yield item
