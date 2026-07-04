"""Optional cross-session memory — degrades to a no-op, never to a crash.

One generic 3-method protocol (ping / remember(kind, text, meta) / recall)
with kinds `driver | wiring_fact | repair_lesson`. The agent-memory-server is
strictly a nice-to-have: absent at boot -> NullMemoryClient; flaky at runtime
-> HttpMemoryClient goes quiet and lazily re-probes. Nothing anywhere blocks
on memory (write sites are fire-and-forget create_task).
"""
