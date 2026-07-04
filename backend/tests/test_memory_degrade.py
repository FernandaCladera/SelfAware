"""Memory degrades to silence, never to a crash: Null no-ops; a dead server
at boot yields the Null client; VectorStore constructs even with no sqlite-vec."""

from selfaware.memory.client import HttpMemoryClient, MemoryClient, NullMemoryClient
from selfaware.memory.vectors import VectorStore


async def test_null_client_noops(noop_memory: NullMemoryClient) -> None:
    assert await noop_memory.ping() is False
    assert await noop_memory.remember("driver", "some text", {"slug": "ldr"}) is None
    assert await noop_memory.recall("anything") == []


async def test_null_client_satisfies_the_protocol(noop_memory: NullMemoryClient) -> None:
    assert isinstance(noop_memory, MemoryClient)


async def test_connect_or_null_against_dead_port_yields_null() -> None:
    client = await HttpMemoryClient.connect_or_null("http://127.0.0.1:1")  # nothing listens on :1
    assert isinstance(client, NullMemoryClient)


async def test_http_client_methods_are_total_when_down() -> None:
    """Even a directly constructed client (no boot ping) never raises."""
    client = HttpMemoryClient("http://127.0.0.1:1", timeout_s=0.2)
    try:
        assert await client.ping() is False
        await client.remember("wiring_fact", "LDR on GP27")  # swallowed, not raised
        assert await client.recall("ldr") == []
    finally:
        await client.aclose()


def test_vector_store_never_raises_at_construction(tmp_path) -> None:
    store = VectorStore(tmp_path / "vec.db")
    if not store.enabled:  # sqlite-vec is an optional extra; both modes legal
        store.add("ldr", "code", "analog", [0.0])
        assert store.knn([0.0]) == []
