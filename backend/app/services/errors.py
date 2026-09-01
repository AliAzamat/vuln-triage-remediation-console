"""One standardized error envelope for the whole API: { error: { code, message } }."""
from __future__ import annotations

from typing import Any, Optional
from fastapi.responses import JSONResponse


def error_response(status: int, code: str, message: str,
                   details: Optional[Any] = None) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "details": details}},
    )
