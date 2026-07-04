# Backend

Python 3.12, uv-managed, FastAPI + PydanticAI. Run: `make dev-backend`
(factory: `selfaware.api.app:create_app`). Tests: `make test` — green with no
.env, no docker, no USB, no API key (`ALLOW_MODEL_REQUESTS=False`).

## Module map

| Package | Responsibility | Key entry points |
|---|---|---|
| `config.py` | Every knob + the PicoBricks pin map; nothing else hardcodes values | `Settings`, `default_specs()` |
| `events/` | The typed language: envelopes, payloads, bus, command routing | `EventBus.publish`, `CommandRouter.dispatch` |
| `hardware/` | Owning the wire: framing, THE lock, mock parity, discovery | `BoardSession.exec/exclusive`, `MockBoard`, `DiscoveryWatcher` |
| `bringup/` | The self-repair loop + deterministic host gates | `CommissionService.enqueue`, `CommissionRunner.run`, `run_gate` |
| `agents/` | LLM roles: driver author + dashboard copilot + streaming bridge | `write_driver`, `copilot_agent`, `run_agent_streaming` |
| `registry/` | Verified capabilities: records + call-time-resolved tools | `DriverRegistry.register/update_code/as_toolset` |
| `memory/` | Optional cross-session memory; no-op when the server is down | `MemoryClient`, `HttpMemoryClient.connect_or_null` |
| `observability/` | logfire → local LGTM; `selfaware.*` span conventions | `configure_observability` |
| `api/` | One WebSocket, tiny REST, lifespan composition root | `create_app` |

## Invariants (do not break while extending)

1. One `asyncio.Lock`, in `BoardSession`. Raw transports never leave `hardware/`.
2. `DriverRegistry.register()` is called only by the commission loop after a
   real on-board pass. Tools re-resolve `registry.get(slug)` at call time.
3. `DriverGenOutput` stays FLAT (reasoning → driver_code → imports_used). No
   nesting, no Optional/Union — flat survives weak structured-output paths.
4. Tracebacks travel verbatim: `ExecResult.stderr` → `commission.traceback`
   event → repair prompt. No layer may trim or paraphrase.
5. No I/O or credential reads at import time. Model resolution happens per run.
6. Mock is explicit (`SELFAWARE_MOCK_BOARD`) — never a silent fallback.

## Where build-day logic lands

| File | Build-day job |
|---|---|
| `hardware/serial_board.py` | the raw-REPL byte dance against the real Pico (`_exec_blocking`) |
| `hardware/watcher.py` | I2C scan-diff + ADC signature classification bodies |
| `agents/prompts/*` | per-class prompt engineering — the biggest quality lever |
| `bringup/plausibility.py` | `liveness_delta` second-sample flow |
| `registry/store.py` | JSON snapshot persistence (optional) |
| `memory/vectors.py` | sqlite-vec KNN + embedding provider (stretch) |
