from __future__ import annotations

import json
from typing import Any, AsyncIterator, Iterator, List

import httpx

from . import _models as m
from ._errors import APIError
from ._version import __version__

DEFAULT_BASE_URL = "https://tokentip.to"
_UA = f"tokentip-python/{__version__}"


def _headers(token: str, idempotency_key: str | None = None) -> dict[str, str]:
    h = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": _UA,
    }
    if idempotency_key:
        h["Idempotency-Key"] = idempotency_key
    return h


def _query(**pairs: Any) -> dict[str, Any]:
    return {k: v for k, v in pairs.items() if v is not None}


def _raise_for_status(resp: httpx.Response) -> None:
    if resp.is_success:
        return
    try:
        body: Any = resp.json()
    except ValueError:
        body = resp.text
    raise APIError.from_response(resp.status_code, body)


def _event_from_data(buffer: list[str]) -> m.Event | None:
    if not buffer:
        return None
    payload = "\n".join(buffer)
    if not payload.strip():
        return None
    return m.Event._from(json.loads(payload))


class TokenTip:
    def __init__(
        self,
        token: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._token = token
        self._http = client or httpx.Client(base_url=base_url, timeout=timeout)
        self.tips = _Tips(self)
        self.key = _Key(self)
        self.webhooks = _Webhooks(self)
        self.operator = _Operator(self)

    def __enter__(self) -> "TokenTip":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self._http.close()

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: Any = None,
        idempotency_key: str | None = None,
    ) -> Any:
        resp = self._http.request(
            method,
            path,
            params=params,
            json=json_body,
            headers=_headers(self._token, idempotency_key),
        )
        _raise_for_status(resp)
        return None if resp.status_code == 204 else resp.json()

    def me(self) -> m.Me:
        return m.Me._from(self._request("GET", "/v1/me"))

    def balance(self) -> m.Balance:
        return m.Balance._from(self._request("GET", "/v1/balance"))

    def stats(self) -> m.Stats:
        return m.Stats._from(self._request("GET", "/v1/stats"))

    def events(self, *, operator: bool = False) -> Iterator[m.Event]:
        path = "/v1/operator/events" if operator else "/v1/events"
        with self._http.stream(
            "GET", path, headers=_headers(self._token) | {"Accept": "text/event-stream"}
        ) as resp:
            _raise_for_status(resp)
            buffer: list[str] = []
            for line in resp.iter_lines():
                if line == "":
                    event = _event_from_data(buffer)
                    buffer = []
                    if event is not None:
                        yield event
                elif line.startswith("data:"):
                    buffer.append(line[5:].lstrip())


class _Tips:
    def __init__(self, c: TokenTip) -> None:
        self._c = c

    def list(
        self,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        status: str | None = None,
    ) -> m.TipList:
        params = _query(limit=limit, cursor=cursor, status=status)
        return m.TipList._from(self._c._request("GET", "/v1/tips", params=params))

    def get(self, tip_id: str) -> m.Tip:
        return m.Tip._from(self._c._request("GET", f"/v1/tips/{tip_id}"))


class _Key:
    def __init__(self, c: TokenTip) -> None:
        self._c = c

    def get(self) -> m.Key:
        return m.Key._from(self._c._request("GET", "/v1/key"))

    def rotate(self, *, idempotency_key: str | None = None) -> m.MintedKey:
        return m.MintedKey._from(
            self._c._request("POST", "/v1/key/rotate", idempotency_key=idempotency_key)
        )


class _Webhooks:
    def __init__(self, c: TokenTip) -> None:
        self._c = c

    def list(self) -> List[m.WebhookEndpoint]:
        rows = self._c._request("GET", "/v1/webhooks")
        return [m.WebhookEndpoint._from(r) for r in rows]

    def create(
        self,
        url: str,
        *,
        events: List[str] | None = None,
        description: str | None = None,
    ) -> m.WebhookEndpointCreated:
        body = _query(url=url, events=events, description=description)
        return m.WebhookEndpointCreated._from(
            self._c._request("POST", "/v1/webhooks", json_body=body)
        )

    def delete(self, webhook_id: str) -> None:
        self._c._request("DELETE", f"/v1/webhooks/{webhook_id}")


class _Operator:
    def __init__(self, c: TokenTip) -> None:
        self._c = c

    def overview(self) -> m.Overview:
        return m.Overview._from(self._c._request("GET", "/v1/operator/overview"))

    def tips(
        self,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        status: str | None = None,
    ) -> m.TipList:
        params = _query(limit=limit, cursor=cursor, status=status)
        return m.TipList._from(
            self._c._request("GET", "/v1/operator/tips", params=params)
        )

    def creators(
        self, *, limit: int | None = None, cursor: str | None = None
    ) -> m.CreatorList:
        params = _query(limit=limit, cursor=cursor)
        return m.CreatorList._from(
            self._c._request("GET", "/v1/operator/creators", params=params)
        )

    def settle(
        self, tip_id: str, *, idempotency_key: str | None = None
    ) -> m.ForceSettleResult:
        return m.ForceSettleResult._from(
            self._c._request(
                "POST",
                f"/v1/operator/tips/{tip_id}/settle",
                idempotency_key=idempotency_key,
            )
        )

    def disable_key(self, handle: str) -> m.Ack:
        return m.Ack._from(
            self._c._request("POST", f"/v1/operator/creators/{handle}/disable-key")
        )


class AsyncTokenTip:
    def __init__(
        self,
        token: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._token = token
        self._http = client or httpx.AsyncClient(base_url=base_url, timeout=timeout)
        self.tips = _AsyncTips(self)
        self.key = _AsyncKey(self)
        self.webhooks = _AsyncWebhooks(self)
        self.operator = _AsyncOperator(self)

    async def __aenter__(self) -> "AsyncTokenTip":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    async def close(self) -> None:
        await self._http.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: Any = None,
        idempotency_key: str | None = None,
    ) -> Any:
        resp = await self._http.request(
            method,
            path,
            params=params,
            json=json_body,
            headers=_headers(self._token, idempotency_key),
        )
        _raise_for_status(resp)
        return None if resp.status_code == 204 else resp.json()

    async def me(self) -> m.Me:
        return m.Me._from(await self._request("GET", "/v1/me"))

    async def balance(self) -> m.Balance:
        return m.Balance._from(await self._request("GET", "/v1/balance"))

    async def stats(self) -> m.Stats:
        return m.Stats._from(await self._request("GET", "/v1/stats"))

    async def events(self, *, operator: bool = False) -> AsyncIterator[m.Event]:
        path = "/v1/operator/events" if operator else "/v1/events"
        async with self._http.stream(
            "GET", path, headers=_headers(self._token) | {"Accept": "text/event-stream"}
        ) as resp:
            _raise_for_status(resp)
            buffer: list[str] = []
            async for line in resp.aiter_lines():
                if line == "":
                    event = _event_from_data(buffer)
                    buffer = []
                    if event is not None:
                        yield event
                elif line.startswith("data:"):
                    buffer.append(line[5:].lstrip())


class _AsyncTips:
    def __init__(self, c: AsyncTokenTip) -> None:
        self._c = c

    async def list(
        self,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        status: str | None = None,
    ) -> m.TipList:
        params = _query(limit=limit, cursor=cursor, status=status)
        return m.TipList._from(await self._c._request("GET", "/v1/tips", params=params))

    async def get(self, tip_id: str) -> m.Tip:
        return m.Tip._from(await self._c._request("GET", f"/v1/tips/{tip_id}"))


class _AsyncKey:
    def __init__(self, c: AsyncTokenTip) -> None:
        self._c = c

    async def get(self) -> m.Key:
        return m.Key._from(await self._c._request("GET", "/v1/key"))

    async def rotate(self, *, idempotency_key: str | None = None) -> m.MintedKey:
        return m.MintedKey._from(
            await self._c._request(
                "POST", "/v1/key/rotate", idempotency_key=idempotency_key
            )
        )


class _AsyncWebhooks:
    def __init__(self, c: AsyncTokenTip) -> None:
        self._c = c

    async def list(self) -> List[m.WebhookEndpoint]:
        rows = await self._c._request("GET", "/v1/webhooks")
        return [m.WebhookEndpoint._from(r) for r in rows]

    async def create(
        self,
        url: str,
        *,
        events: List[str] | None = None,
        description: str | None = None,
    ) -> m.WebhookEndpointCreated:
        body = _query(url=url, events=events, description=description)
        return m.WebhookEndpointCreated._from(
            await self._c._request("POST", "/v1/webhooks", json_body=body)
        )

    async def delete(self, webhook_id: str) -> None:
        await self._c._request("DELETE", f"/v1/webhooks/{webhook_id}")


class _AsyncOperator:
    def __init__(self, c: AsyncTokenTip) -> None:
        self._c = c

    async def overview(self) -> m.Overview:
        return m.Overview._from(await self._c._request("GET", "/v1/operator/overview"))

    async def tips(
        self,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        status: str | None = None,
    ) -> m.TipList:
        params = _query(limit=limit, cursor=cursor, status=status)
        return m.TipList._from(
            await self._c._request("GET", "/v1/operator/tips", params=params)
        )

    async def creators(
        self, *, limit: int | None = None, cursor: str | None = None
    ) -> m.CreatorList:
        params = _query(limit=limit, cursor=cursor)
        return m.CreatorList._from(
            await self._c._request("GET", "/v1/operator/creators", params=params)
        )

    async def settle(
        self, tip_id: str, *, idempotency_key: str | None = None
    ) -> m.ForceSettleResult:
        return m.ForceSettleResult._from(
            await self._c._request(
                "POST",
                f"/v1/operator/tips/{tip_id}/settle",
                idempotency_key=idempotency_key,
            )
        )

    async def disable_key(self, handle: str) -> m.Ack:
        return m.Ack._from(
            await self._c._request(
                "POST", f"/v1/operator/creators/{handle}/disable-key"
            )
        )
