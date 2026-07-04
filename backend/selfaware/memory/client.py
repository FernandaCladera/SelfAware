"""MemoryClient protocol + the two implementations (HTTP and Null).

Total-by-construction: every public method on both clients swallows transport
errors and returns the empty value — callers NEVER branch on availability.
The only availability signal anyone may surface is the copilot's `recall`
tool answering "memory offline" when it holds a NullMemoryClient (the honest
degrade, per the degradation matrix).

Build-day note: agent-memory-server REST paths below are best-guess from the
image docs (/v1/long-term-memory/, /v1/long-term-memory/search, /v1/health) —
UNCONFIRMED; verify against http://localhost:8100/docs once `make infra-up`
runs, adjust _REMEMBER_PATH/_SEARCH_PATH only.
"""

import time
from typing import Any, Protocol, runtime_checkable
from uuid import uuid4

import httpx

DEFAULT_TIMEOUT_S = 2.0
REPROBE_INTERVAL_S = 30.0

MEMORY_KINDS = ("driver", "wiring_fact", "repair_lesson")

_PING_PATH = "/v1/health"
_PING_FALLBACK_PATH = "/docs"
_REMEMBER_PATH = "/v1/long-term-memory/"
_SEARCH_PATH = "/v1/long-term-memory/search"


@runtime_checkable
class MemoryClient(Protocol):
    """The generic 3-method memory surface. kinds: driver|wiring_fact|repair_lesson."""

    async def ping(self) -> bool: ...

    async def remember(self, kind: str, text: str, meta: dict[str, Any] | None = None) -> None: ...

    async def recall(self, query: str, limit: int = 5) -> list[str]: ...


class NullMemoryClient:
    """Memory that honestly does not exist. Every method is a cheap no-op."""

    async def ping(self) -> bool:
        return False

    async def remember(self, kind: str, text: str, meta: dict[str, Any] | None = None) -> None:
        return None

    async def recall(self, query: str, limit: int = 5) -> list[str]:
        return []


class HttpMemoryClient:
    """Async client for redis/agent-memory-server over plain httpx.

    Runtime degrade: any transport error flips the client 'down'; while down,
    calls no-op instantly and a re-probe is attempted at most every 30s — so a
    late `make infra-up` self-heals without a backend restart.
    """

    def __init__(self, base_url: str, timeout_s: float = DEFAULT_TIMEOUT_S) -> None:
        self._client = httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=timeout_s)
        self._down_since: float | None = None  # None == believed up

    @classmethod
    async def connect_or_null(cls, base_url: str, timeout_s: float = DEFAULT_TIMEOUT_S) -> MemoryClient:
        """Boot-time factory: ping once; a dead server means NullMemoryClient.

        The lifespan calls this exactly once — no other code decides between
        implementations, so the degrade path has one door.
        """
        client = cls(base_url, timeout_s=timeout_s)
        if await client.ping():
            return client
        await client.aclose()
        return NullMemoryClient()

    async def aclose(self) -> None:
        await self._client.aclose()

    # --- MemoryClient ------------------------------------------------------------

    async def ping(self) -> bool:
        try:
            resp = await self._client.get(_PING_PATH)
            if resp.status_code >= 500:
                raise httpx.HTTPStatusError("unhealthy", request=resp.request, response=resp)
            if resp.status_code == 404:  # older images: no /v1/health — try the docs page
                resp = await self._client.get(_PING_FALLBACK_PATH)
                resp.raise_for_status()
        except Exception:  # noqa: BLE001 — a dead memory server is a shrug, not an error
            self._down_since = time.monotonic()
            return False
        self._down_since = None
        return True

    async def remember(self, kind: str, text: str, meta: dict[str, Any] | None = None) -> None:
        """Store one long-term memory. Fire-and-forget friendly: never raises."""
        if not await self._usable():
            return
        record = {
            "id": uuid4().hex,
            "text": text,
            "memory_type": "semantic",
            "topics": [kind],
            "namespace": "selfaware",
        }
        if meta:
            record["metadata"] = meta
        try:
            await self._client.post(_REMEMBER_PATH, json={"memories": [record]})
        except Exception:  # noqa: BLE001
            self._down_since = time.monotonic()

    async def recall(self, query: str, limit: int = 5) -> list[str]:
        """Semantic/keyword search; [] when down (or when the server has no
        embeddings key — semantic search needs one, degradation matrix)."""
        if not await self._usable():
            return []
        try:
            resp = await self._client.post(_SEARCH_PATH, json={"text": query, "limit": limit})
            resp.raise_for_status()
            body = resp.json()
        except Exception:  # noqa: BLE001
            self._down_since = time.monotonic()
            return []
        memories = body.get("memories", body.get("results", [])) if isinstance(body, dict) else []
        return [m.get("text", "") for m in memories if isinstance(m, dict) and m.get("text")][:limit]

    # --- internals -----------------------------------------------------------------

    async def _usable(self) -> bool:
        """Up, or down-but-due-a-reprobe (lazy, at most every 30s)."""
        if self._down_since is None:
            return True
        if time.monotonic() - self._down_since < REPROBE_INTERVAL_S:
            return False
        return await self.ping()
