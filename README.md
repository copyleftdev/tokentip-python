# tokentip — Python SDK

[![Tip my tokens](https://tokentip.to/badge/copyleftdev.svg?logo=1)](https://tokentip.to/@copyleftdev)

Official Python client for the [TokenTip API](https://tokentip.to). Tips that buy
AI inference credit for open-source maintainers. Typed, sync **and** async, with
webhook signature verification and a live event stream.

```sh
pip install tokentip
```

Requires Python 3.10+. The only runtime dependency is `httpx`.

## Quickstart

Mint an API token in your dashboard (`tt_…`), then:

```python
from tokentip import TokenTip

with TokenTip("tt_your_token") as tt:
    me = tt.me()
    print(me.handle, me.credit)          # credit is a decimal.Decimal, never a float

    tips = tt.tips.list(status="settled", limit=20)
    for tip in tips.data:
        print(tip.id, tip.net_to_tokens)
```

Money is always parsed to `decimal.Decimal` — exact, never binary-rounded.

## Async

Every call has an async twin with the same shape:

```python
from tokentip import AsyncTokenTip

async with AsyncTokenTip("tt_your_token") as tt:
    balance = await tt.balance()
    async for event in tt.events():
        if event.type == "tip.settled":
            print("settled", event.tip.creator_handle, "→", event.balance)
```

## The live event stream (SSE)

`events()` opens `GET /v1/events` and yields decoded `Event` objects until you stop
iterating. Pass `operator=True` (operator token) for the system-wide stream.

```python
with TokenTip("tt_your_token") as tt:
    for event in tt.events():
        match event.type:
            case "tip.settled":
                print("credit granted:", event.tip.net_to_tokens)
            case "key.rotated":
                print("key rotated for", event.data["creator_handle"])
```

Events carry an idempotency `id` — dedupe on it, TokenTip may redeliver.

## Webhooks

Register an endpoint and receive the same events over signed POSTs:

```python
created = tt.webhooks.create("https://you.example/hook", events=["tip.settled"])
print(created.secret)   # whsec_… — shown once, store it now
```

Verify each delivery (constant-time, with timestamp tolerance):

```python
from tokentip import webhooks

# in your web handler:
event = webhooks.verify(
    request.body,                                    # raw bytes/str, unparsed
    request.headers["X-TokenTip-Signature"],
    signing_secret,                                  # the whsec_… from create()
)
# raises SignatureVerificationError on a bad signature or stale timestamp
```

## Operator

With an operator-scoped token:

```python
overview = tt.operator.overview()
print(overview.pool.state, overview.pool.committed)

result = tt.operator.settle(tip_id)                  # force-settle a held tip
tt.operator.disable_key("some-handle")               # fraud kill-switch
```

## Errors

Non-2xx responses raise a typed subclass of `APIError`, carrying the RFC 7807
problem detail:

| HTTP | Exception              |
|------|------------------------|
| 401  | `AuthenticationError`  |
| 403  | `ForbiddenError`       |
| 404  | `NotFoundError`        |
| 409  | `ConflictError`        |
| 502  | `UpstreamError`        |

```python
from tokentip import NotFoundError

try:
    tt.tips.get("does-not-exist")
except NotFoundError as e:
    print(e.status, e.title, e.detail)
```

## Idempotency

Mutating calls that can safely be retried accept an idempotency key:

```python
tt.key.rotate(idempotency_key="rotate-2026-07-19")
tt.operator.settle(tip_id, idempotency_key=tip_id)
```

## Reference

The full contract lives in the [`api/`](https://tokentip.to) OpenAPI + AsyncAPI
specs; this SDK is generated to match them.
