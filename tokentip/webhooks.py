from __future__ import annotations

import hashlib
import hmac
import json
import time

from ._errors import SignatureVerificationError
from ._models import Event

DEFAULT_TOLERANCE = 300


def _parse_header(header: str) -> tuple[int, str]:
    parts = dict(
        p.split("=", 1) for p in header.split(",") if "=" in p
    )
    if "t" not in parts or "v1" not in parts:
        raise SignatureVerificationError("malformed X-TokenTip-Signature header")
    try:
        return int(parts["t"]), parts["v1"]
    except ValueError as exc:
        raise SignatureVerificationError("invalid timestamp in signature") from exc


def verify(
    payload: str | bytes,
    signature_header: str,
    secret: str,
    tolerance: int = DEFAULT_TOLERANCE,
) -> Event:
    body = payload.decode() if isinstance(payload, bytes) else payload
    timestamp, provided = _parse_header(signature_header)

    if tolerance and abs(time.time() - timestamp) > tolerance:
        raise SignatureVerificationError("signature timestamp outside tolerance")

    expected = hmac.new(
        secret.encode(), f"{timestamp}.{body}".encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, provided):
        raise SignatureVerificationError("signature mismatch")

    return Event._from(json.loads(body))
