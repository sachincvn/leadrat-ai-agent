"""Request-scoped context.

The Leadrat JWT belongs to the caller, not to the process, so it travels in a
ContextVar: the API sets it once per request and the CRM client reads it deep
down the stack without every layer having to pass it along.
"""

from contextlib import contextmanager
from contextvars import ContextVar

_jwt: ContextVar[str | None] = ContextVar("leadrat_jwt", default=None)


def get_jwt() -> str | None:
    return _jwt.get()


@contextmanager
def use_jwt(token: str | None):
    reset = _jwt.set(token)
    try:
        yield
    finally:
        _jwt.reset(reset)
