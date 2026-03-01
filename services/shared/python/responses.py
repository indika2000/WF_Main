import json
from datetime import datetime, timezone
from typing import Any

from starlette.responses import Response


class _DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that handles datetime objects."""

    def default(self, o: Any) -> Any:
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)


def _json_response(content: dict, status_code: int) -> Response:
    """Build a JSON response that handles datetime serialisation."""
    body = json.dumps(content, cls=_DateTimeEncoder)
    return Response(
        content=body,
        status_code=status_code,
        media_type="application/json",
    )


def success_response(
    data: Any = None,
    message: str = "Success",
    status_code: int = 200,
) -> Response:
    """Return a standardized success response."""
    return _json_response(
        content={
            "success": True,
            "message": message,
            "data": data,
        },
        status_code=status_code,
    )


def error_response(
    message: str = "An error occurred",
    error_code: str = "INTERNAL_ERROR",
    status_code: int = 400,
    detail: str | None = None,
) -> Response:
    """Return a standardized error response."""
    content: dict[str, Any] = {
        "success": False,
        "message": message,
        "error_code": error_code,
    }
    if detail is not None:
        content["detail"] = detail
    return _json_response(content=content, status_code=status_code)
