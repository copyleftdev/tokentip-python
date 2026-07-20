from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any


def _dec(v: Any) -> Decimal:
    return Decimal(v)


def _dec_opt(v: Any) -> Decimal | None:
    return None if v is None else Decimal(v)


def _dt(v: Any) -> datetime:
    return datetime.fromisoformat(v)


def _dt_opt(v: Any) -> datetime | None:
    return None if v is None else datetime.fromisoformat(v)


@dataclass(frozen=True, slots=True)
class Tip:
    id: str
    creator_handle: str
    status: str
    gross: Decimal
    net_to_tokens: Decimal
    created_at: datetime
    tipper_name: str | None = None
    tipper_note: str | None = None
    held_at: datetime | None = None
    settled_at: datetime | None = None

    @classmethod
    def _from(cls, d: dict[str, Any]) -> "Tip":
        return cls(
            id=d["id"],
            creator_handle=d["creator_handle"],
            status=d["status"],
            gross=_dec(d["gross"]),
            net_to_tokens=_dec(d["net_to_tokens"]),
            created_at=_dt(d["created_at"]),
            tipper_name=d.get("tipper_name"),
            tipper_note=d.get("tipper_note"),
            held_at=_dt_opt(d.get("held_at")),
            settled_at=_dt_opt(d.get("settled_at")),
        )


@dataclass(frozen=True, slots=True)
class TipList:
    data: list[Tip]
    next_cursor: str | None = None

    @classmethod
    def _from(cls, d: dict[str, Any]) -> "TipList":
        return cls([Tip._from(t) for t in d["data"]], d.get("next_cursor"))


@dataclass(frozen=True, slots=True)
class Me:
    handle: str
    display_name: str
    credit: Decimal
    key_claimed: bool
    key_fingerprint: str | None = None
    created_at: datetime | None = None

    @classmethod
    def _from(cls, d: dict[str, Any]) -> "Me":
        return cls(
            handle=d["handle"],
            display_name=d["display_name"],
            credit=_dec(d["credit"]),
            key_claimed=d["key_claimed"],
            key_fingerprint=d.get("key_fingerprint"),
            created_at=_dt_opt(d.get("created_at")),
        )


@dataclass(frozen=True, slots=True)
class Balance:
    credit: Decimal
    key_claimed: bool
    live_usage: Decimal | None = None
    live_limit: Decimal | None = None
    disabled: bool | None = None

    @classmethod
    def _from(cls, d: dict[str, Any]) -> "Balance":
        return cls(
            credit=_dec(d["credit"]),
            key_claimed=d["key_claimed"],
            live_usage=_dec_opt(d.get("live_usage")),
            live_limit=_dec_opt(d.get("live_limit")),
            disabled=d.get("disabled"),
        )


@dataclass(frozen=True, slots=True)
class Key:
    fingerprint: str
    disabled: bool
    minted_at: datetime | None = None
    usage: Decimal | None = None
    limit: Decimal | None = None

    @classmethod
    def _from(cls, d: dict[str, Any]) -> "Key":
        return cls(
            fingerprint=d["fingerprint"],
            disabled=d["disabled"],
            minted_at=_dt_opt(d.get("minted_at")),
            usage=_dec_opt(d.get("usage")),
            limit=_dec_opt(d.get("limit")),
        )


@dataclass(frozen=True, slots=True)
class MintedKey:
    secret: str
    fingerprint: str
    limit: Decimal
    minted_at: datetime | None = None

    @classmethod
    def _from(cls, d: dict[str, Any]) -> "MintedKey":
        return cls(
            secret=d["secret"],
            fingerprint=d["fingerprint"],
            limit=_dec(d["limit"]),
            minted_at=_dt_opt(d.get("minted_at")),
        )


@dataclass(frozen=True, slots=True)
class Stats:
    tips_total: int
    tips_settled: int
    tips_held: int
    settled_gross: Decimal
    settled_net: Decimal
    lifetime_gross: Decimal

    @classmethod
    def _from(cls, d: dict[str, Any]) -> "Stats":
        return cls(
            tips_total=d["tips_total"],
            tips_settled=d["tips_settled"],
            tips_held=d["tips_held"],
            settled_gross=_dec(d["settled_gross"]),
            settled_net=_dec(d["settled_net"]),
            lifetime_gross=_dec(d["lifetime_gross"]),
        )


@dataclass(frozen=True, slots=True)
class WebhookEndpoint:
    id: str
    url: str
    disabled: bool
    events: list[str] = field(default_factory=list)
    created_at: datetime | None = None

    @classmethod
    def _from(cls, d: dict[str, Any]) -> "WebhookEndpoint":
        return cls(
            id=d["id"],
            url=d["url"],
            disabled=d["disabled"],
            events=d.get("events") or [],
            created_at=_dt_opt(d.get("created_at")),
        )


@dataclass(frozen=True, slots=True)
class WebhookEndpointCreated:
    id: str
    url: str
    disabled: bool
    secret: str
    events: list[str] = field(default_factory=list)
    created_at: datetime | None = None

    @classmethod
    def _from(cls, d: dict[str, Any]) -> "WebhookEndpointCreated":
        return cls(
            id=d["id"],
            url=d["url"],
            disabled=d["disabled"],
            secret=d["secret"],
            events=d.get("events") or [],
            created_at=_dt_opt(d.get("created_at")),
        )


@dataclass(frozen=True, slots=True)
class Pool:
    committed: Decimal
    state: str
    available: Decimal | None = None
    headroom: Decimal | None = None

    @classmethod
    def _from(cls, d: dict[str, Any]) -> "Pool":
        return cls(
            committed=_dec(d["committed"]),
            state=d["state"],
            available=_dec_opt(d.get("available")),
            headroom=_dec_opt(d.get("headroom")),
        )


@dataclass(frozen=True, slots=True)
class Overview:
    pool: Pool
    counts: dict[str, int]
    money: dict[str, Decimal]
    tips_by_status: dict[str, int]

    @classmethod
    def _from(cls, d: dict[str, Any]) -> "Overview":
        money = {k: _dec(v) for k, v in (d.get("money") or {}).items()}
        return cls(
            pool=Pool._from(d["pool"]),
            counts=d.get("counts") or {},
            money=money,
            tips_by_status=d.get("tips_by_status") or {},
        )


@dataclass(frozen=True, slots=True)
class CreatorSummary:
    handle: str
    balance: Decimal
    key_claimed: bool
    display_name: str | None = None
    fingerprint: str | None = None
    live_usage: Decimal | None = None
    live_limit: Decimal | None = None
    disabled: bool | None = None
    settled_tips: int | None = None
    settled_gross: Decimal | None = None
    joined: datetime | None = None

    @classmethod
    def _from(cls, d: dict[str, Any]) -> "CreatorSummary":
        return cls(
            handle=d["handle"],
            balance=_dec(d["balance"]),
            key_claimed=d["key_claimed"],
            display_name=d.get("display_name"),
            fingerprint=d.get("fingerprint"),
            live_usage=_dec_opt(d.get("live_usage")),
            live_limit=_dec_opt(d.get("live_limit")),
            disabled=d.get("disabled"),
            settled_tips=d.get("settled_tips"),
            settled_gross=_dec_opt(d.get("settled_gross")),
            joined=_dt_opt(d.get("joined")),
        )


@dataclass(frozen=True, slots=True)
class CreatorList:
    data: list[CreatorSummary]
    next_cursor: str | None = None

    @classmethod
    def _from(cls, d: dict[str, Any]) -> "CreatorList":
        return cls([CreatorSummary._from(c) for c in d["data"]], d.get("next_cursor"))


@dataclass(frozen=True, slots=True)
class ForceSettleResult:
    status: str
    message: str

    @classmethod
    def _from(cls, d: dict[str, Any]) -> "ForceSettleResult":
        return cls(status=d["status"], message=d["message"])


@dataclass(frozen=True, slots=True)
class Ack:
    ok: bool
    message: str | None = None

    @classmethod
    def _from(cls, d: dict[str, Any]) -> "Ack":
        return cls(ok=d["ok"], message=d.get("message"))


@dataclass(frozen=True, slots=True)
class Event:
    id: str
    type: str
    created: datetime
    scope: str
    data: dict[str, Any]
    api_version: str | None = None

    @classmethod
    def _from(cls, d: dict[str, Any]) -> "Event":
        return cls(
            id=d["id"],
            type=d["type"],
            created=_dt(d["created"]),
            scope=d["scope"],
            data=d.get("data") or {},
            api_version=d.get("api_version"),
        )

    @property
    def tip(self) -> Tip | None:
        raw = self.data.get("tip")
        return Tip._from(raw) if raw else None

    @property
    def balance(self) -> Decimal | None:
        return _dec_opt(self.data.get("balance"))
