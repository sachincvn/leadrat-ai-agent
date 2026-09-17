"""Domain errors and their HTTP mapping."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class MusoError(Exception):
    status_code = 500
    code = "internal_error"

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class LeadNotFoundError(MusoError):
    status_code = 404
    code = "lead_not_found"


class AuthError(MusoError):
    status_code = 401
    code = "unauthorized"


class CRMError(MusoError):
    status_code = 502
    code = "crm_error"


class LLMError(MusoError):
    status_code = 503
    code = "llm_error"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(MusoError)
    async def _handler(_: Request, exc: MusoError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )
