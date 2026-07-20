import hashlib
import hmac
import json
import time
from decimal import Decimal

import httpx
import pytest

from tokentip import (
    AsyncTokenTip,
    ForbiddenError,
    NotFoundError,
    TokenTip,
    webhooks,
)
from tokentip._errors import SignatureVerificationError

TIP = {
    "id": "369330cb-ae6e-4cc9-a7e8-a9b95e89aacd",
    "creator_handle": "copyleftdev",
    "status": "settled",
    "gross": "5.000000",
    "net_to_tokens": "4.068225",
    "tipper_name": None,
    "tipper_note": None,
    "created_at": "2026-07-19T10:03:00+00:00",
    "held_at": "2026-07-19T10:03:20+00:00",
    "settled_at": "2026-07-19T10:07:00+00:00",
}


def handler(request: httpx.Request) -> httpx.Response:
    assert request.headers["authorization"] == "Bearer tt_test"
    path = request.url.path
    if path == "/v1/me":
        return httpx.Response(
            200,
            json={
                "handle": "copyleftdev",
                "display_name": "DJ",
                "credit": "4.068225",
                "key_claimed": True,
                "key_fingerprint": "sk-or-v1-117...2dce",
                "created_at": "2026-07-01T00:00:00+00:00",
            },
        )
    if path == "/v1/tips":
        assert request.url.params["status"] == "settled"
        return httpx.Response(200, json={"data": [TIP], "next_cursor": None})
    if path == "/v1/operator/overview":
        return httpx.Response(
            403,
            json={"title": "not an operator", "status": 403, "detail": "operator only"},
        )
    if path.startswith("/v1/tips/"):
        return httpx.Response(404, json={"title": "not found", "status": 404})
    if path == "/v1/webhooks" and request.method == "POST":
        body = json.loads(request.content)
        assert body["url"] == "https://example.com/hook"
        return httpx.Response(
            201,
            json={
                "id": "whep_1",
                "url": body["url"],
                "events": body.get("events", []),
                "created_at": "2026-07-19T00:00:00+00:00",
                "disabled": False,
                "secret": "whsec_abc",
            },
        )
    raise AssertionError(f"unexpected {request.method} {path}")


def make_client() -> TokenTip:
    return TokenTip(
        "tt_test", client=httpx.Client(base_url="https://tokentip.to", transport=httpx.MockTransport(handler))
    )


def test_me_parses_decimal():
    with make_client() as c:
        me = c.me()
    assert me.handle == "copyleftdev"
    assert me.credit == Decimal("4.068225")
    assert isinstance(me.credit, Decimal)


def test_list_tips_filter_and_parse():
    with make_client() as c:
        tips = c.tips.list(status="settled")
    assert tips.next_cursor is None
    assert tips.data[0].net_to_tokens == Decimal("4.068225")


def test_forbidden_maps_to_typed_error():
    with make_client() as c:
        with pytest.raises(ForbiddenError) as exc:
            c.operator.overview()
    assert exc.value.status == 403


def test_not_found():
    with make_client() as c:
        with pytest.raises(NotFoundError):
            c.tips.get("missing")


def test_create_webhook_returns_secret_once():
    with make_client() as c:
        created = c.webhooks.create("https://example.com/hook", events=["tip.settled"])
    assert created.secret == "whsec_abc"
    assert created.events == ["tip.settled"]


async def test_async_me():
    async with AsyncTokenTip(
        "tt_test",
        client=httpx.AsyncClient(
            base_url="https://tokentip.to", transport=httpx.MockTransport(handler)
        ),
    ) as c:
        me = await c.me()
    assert me.credit == Decimal("4.068225")


def _sign(body: str, secret: str, ts: int) -> str:
    mac = hmac.new(secret.encode(), f"{ts}.{body}".encode(), hashlib.sha256).hexdigest()
    return f"t={ts},v1={mac}"


def test_webhook_verify_roundtrip():
    body = json.dumps(
        {
            "id": "evt_1",
            "type": "tip.settled",
            "created": "2026-07-19T10:07:00+00:00",
            "scope": "creator",
            "data": {"tip": TIP, "balance": "4.068225"},
        }
    )
    ts = int(time.time())
    event = webhooks.verify(body, _sign(body, "whsec_abc", ts), "whsec_abc")
    assert event.type == "tip.settled"
    assert event.balance == Decimal("4.068225")
    assert event.tip.creator_handle == "copyleftdev"


def test_webhook_verify_rejects_tampered_body():
    body = '{"id":"evt_1","type":"tip.settled","created":"2026-07-19T10:07:00+00:00","scope":"creator","data":{}}'
    ts = int(time.time())
    sig = _sign(body, "whsec_abc", ts)
    with pytest.raises(SignatureVerificationError):
        webhooks.verify(body + " ", sig, "whsec_abc")


def test_webhook_verify_rejects_stale_timestamp():
    body = "{}"
    old = int(time.time()) - 10_000
    with pytest.raises(SignatureVerificationError):
        webhooks.verify(body, _sign(body, "whsec_abc", old), "whsec_abc")
