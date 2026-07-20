from __future__ import annotations

from typing import Any


class TokenTipError(Exception):
    pass


class APIError(TokenTipError):
    def __init__(
        self,
        status: int,
        title: str,
        detail: str | None = None,
        type: str = "about:blank",
        instance: str | None = None,
        body: Any = None,
    ) -> None:
        self.status = status
        self.title = title
        self.detail = detail
        self.type = type
        self.instance = instance
        self.body = body
        super().__init__(f"{status} {title}" + (f": {detail}" if detail else ""))

    @classmethod
    def from_response(cls, status: int, body: Any) -> "APIError":
        problem = body if isinstance(body, dict) else {}
        klass = _BY_STATUS.get(status, cls)
        return klass(
            status=problem.get("status", status),
            title=problem.get("title", "request failed"),
            detail=problem.get("detail"),
            type=problem.get("type", "about:blank"),
            instance=problem.get("instance"),
            body=body,
        )


class AuthenticationError(APIError):
    pass


class ForbiddenError(APIError):
    pass


class NotFoundError(APIError):
    pass


class ConflictError(APIError):
    pass


class UpstreamError(APIError):
    pass


class SignatureVerificationError(TokenTipError):
    pass


_BY_STATUS: dict[int, type[APIError]] = {
    401: AuthenticationError,
    403: ForbiddenError,
    404: NotFoundError,
    409: ConflictError,
    502: UpstreamError,
}
