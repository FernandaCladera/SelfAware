# Frontend — the agent theater

Vite + React + TS + zustand. Run: `make dev-frontend` (:5173). The frontend is
a **theater, not a dashboard**: the backend narrates the loop as typed events;
the UI stages them. Two seams make every event a two-file change:

- `state/dispatch.ts` — THE exhaustive switch (a `never` check makes a new
  event type a compile error) mapping events → slice mutations.
- `theater/registry.ts` — event type → feed row renderer + which panel pulses.

Unknown event types are never dropped: they render as `RawEventRow` in the feed.

## Structure

| Dir | Contents |
|---|---|
| `types/` | `events.ts` (contract mirror — see docs/event-protocol.md), `domain.ts` |
| `lib/` | `ws.ts` (reconnect + jittered backoff), `transport.ts` (ws \| fixture), `fixturePlayer.ts`, `parse.ts` (envelope guard), `ring.ts` |
| `state/` | zustand store + slices: connection, board, commission (trail of `StageRecord`s incl. repair loop-backs), feed (ring 500), drivers (+ discovery presences), readings (ring 512/slug + version counters), chat |
| `theater/` | registry, `EventFeed`, rows, `pulse.ts` (panel flash pub/sub) |
| `components/` | primitives (`Panel`, `StatusDot`, `MachineText`) + panels (`CommissionStepper`, `TracebackPane`, `ReadingScope`, `DeviceRail`, `ChatDock`, `BoardStatus`) |
| `routes/` | `Landing` (pitch + teaser loop + "> enter the console"), `Console` (grid) |
| `fixtures/` | `commission-ldr.json` (canonical demo narrative — doubles as the backend's contract test), `teaser.json` |
| `styles/` | `tokens.css` (ALL design tokens), `base.css` |

## Mock mode

`/app?mock=1` (or `VITE_MOCK=1`) swaps the WebSocket for a `FixturePlayer`
replaying `commission-ldr.json` — the full fail→repair→pass narrative with
zero backend. The landing teaser always uses its own player. **If the backend
can emit the fixture's exact sequence, the whole UI works** — that's the
contract test.

## Performance rule

`sensor.reading` events go into per-slug ring buffers with a version counter;
`ReadingScope` draws via `requestAnimationFrame` + zustand transient
`subscribe` — **no React re-render per sample**. Keep it that way.

## Design direction (build-day craft pass)

Dark instrument in a quiet room. Three surface steps, hairlines not shadows,
ONE phosphor accent (`--phosphor`), `--alert` red RESERVED for verbatim
tracebacks/failures, machine voice (mono) vs UI voice (humanist). Motion:
events arrive as pulses (`--pulse-ms`), the stepper is the protagonist,
tracebacks interrupt without easing, the scope is the only thing that idles.
Banned: white cards, drop shadows, gradient CTAs, KPI tile grids.
