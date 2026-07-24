from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable, Generic, Iterable, TypeVar


T = TypeVar("T")
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200
_CURSOR_CONTEXT = b"alphapilot-v63.1-cursor-v1"


class CursorError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class CursorPage(Generic[T]):
    items: list[T]
    pageSize: int
    nextCursor: str | None
    hasMore: bool
    stateVersion: str

    def to_dict(self) -> dict[str, object]:
        return {
            "items": self.items,
            "pageSize": self.pageSize,
            "nextCursor": self.nextCursor,
            "hasMore": self.hasMore,
            "stateVersion": self.stateVersion,
        }


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _signature(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_CURSOR_CONTEXT + _canonical_bytes(payload)).hexdigest()


def encode_cursor(
    *,
    scope: str,
    state_version: str,
    last: tuple[Any, ...],
) -> str:
    if not scope.strip() or not state_version.strip() or not last:
        raise ValueError("scope, state_version and last are required")
    payload = {
        "version": 1,
        "scope": scope,
        "stateVersion": state_version,
        "last": list(last),
    }
    envelope = {"payload": payload, "digest": _signature(payload)}
    raw = _canonical_bytes(envelope)
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_cursor(value: str, *, scope: str) -> dict[str, Any]:
    try:
        padding = "=" * (-len(value) % 4)
        raw = base64.urlsafe_b64decode((value + padding).encode("ascii"))
        envelope = json.loads(raw.decode("utf-8"))
        payload = envelope["payload"]
        digest = envelope["digest"]
    except (ValueError, UnicodeError, json.JSONDecodeError, KeyError, TypeError) as error:
        raise CursorError("cursor_invalid") from error
    if not isinstance(payload, dict) or digest != _signature(payload):
        raise CursorError("cursor_invalid")
    if payload.get("scope") != scope:
        raise CursorError("cursor_scope_mismatch")
    last = payload.get("last")
    if not isinstance(last, list):
        raise CursorError("cursor_invalid")
    return payload


def normalize_page_size(limit: int | str | None) -> int:
    try:
        parsed = int(limit if limit is not None else DEFAULT_PAGE_SIZE)
    except (TypeError, ValueError):
        parsed = DEFAULT_PAGE_SIZE
    return max(1, min(parsed, MAX_PAGE_SIZE))


def paginate_items(
    items: Iterable[T],
    *,
    limit: int | str | None,
    cursor: str | None,
    scope: str,
    state_version: str,
    key: Callable[[T], tuple[Any, ...]],
) -> CursorPage[T]:
    if not scope.strip() or not state_version.strip():
        raise ValueError("scope and state_version are required")
    page_size = normalize_page_size(limit)
    ordered = sorted(items, key=key, reverse=True)
    if cursor:
        decoded = decode_cursor(cursor, scope=scope)
        if decoded.get("stateVersion") != state_version:
            raise CursorError("cursor_state_version_mismatch")
        last = decoded.get("last")
        if not isinstance(last, list):
            raise CursorError("cursor_invalid")
        last_key = tuple(last)
        ordered = [item for item in ordered if key(item) < last_key]

    selected = ordered[: page_size + 1]
    has_more = len(selected) > page_size
    page_items = selected[:page_size]
    next_cursor = None
    if has_more and page_items:
        next_cursor = encode_cursor(
            scope=scope,
            state_version=state_version,
            last=key(page_items[-1]),
        )
    return CursorPage(
        items=page_items,
        pageSize=page_size,
        nextCursor=next_cursor,
        hasMore=has_more,
        stateVersion=state_version,
    )
