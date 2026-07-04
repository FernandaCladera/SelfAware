"""DiscoveryWatcher — the plug-in -> materialize demo beat.

Rides its own periodic task but reaches the wire ONLY through session.exec
(lock-acquiring), so a scan can never interleave with a commission or a tool
call and corrupt raw-REPL framing — the lock serializes everything (invariant
#3). During a commission the session holds the lock exclusively; the watcher's
next scan simply waits it out.

Honesty floor, encoded in confidence levels:
  * i2c + KNOWN_I2C_DEVICES hit -> confidence "exact" + suggested_spec
    (one-click commission in the DeviceRail).
  * adc signature change        -> confidence "unknown" — "something on GP27,
    what is it?" — the HUMAN names it; a voltage cannot reveal the part.
    (ADC classification is not wired yet — see _classify_adc.)
"""

import ast
import asyncio
import contextlib

from selfaware.config import Settings
from selfaware.events.bus import EventBus
from selfaware.events.payloads import DeviceFoundPayload, DeviceLostPayload
from selfaware.events.types import EventType
from selfaware.hardware.discovery import I2C_SCAN_SNIPPET, KNOWN_I2C_DEVICES
from selfaware.hardware.session import BoardSession


class DiscoveryWatcher:
    """Periodic I2C-scan diffing -> discovery.device_found / device_lost."""

    def __init__(self, session: BoardSession, bus: EventBus, settings: Settings) -> None:
        self._session = session
        self._bus = bus
        self._settings = settings
        self._known_addrs: set[int] = set()  # last I2C scan result, for diffing
        self._task: asyncio.Task[None] | None = None
        self._interval_s = settings.discovery_interval_s

    async def start(self) -> None:
        """Spawn the watch task. Idempotent."""
        if self._task is not None:
            return
        self._task = asyncio.create_task(self._watch_loop(), name="selfaware-discovery")

    async def stop(self) -> None:
        """Cancel + reap the watch task (the lock drains any in-flight scan
        before the cancel lands — same discipline as the poller)."""
        if self._task is None:
            return
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def _watch_loop(self) -> None:
        while True:
            try:
                await self._scan_once()
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001 — discovery must never kill itself
                pass
            await asyncio.sleep(self._interval_s)

    async def _scan_once(self) -> None:
        """One I2C scan through session.exec (LOCK-acquiring), then diff.

        Skips silently with no link — discovery is ambience, not a health check.
        """
        if not self._session.transport.connected:
            return
        snippet = I2C_SCAN_SNIPPET.format(
            sda=self._settings.pins_i2c_sda, scl=self._settings.pins_i2c_scl
        )
        result = await self._session.exec(snippet)
        if not result.ok:
            return  # a scan traceback/timeout is noise, not a discovery event
        try:
            scanned = {int(a) for a in ast.literal_eval(result.last_line)} if result.last_line else set()
        except (ValueError, SyntaxError, TypeError):
            return
        self._diff_i2c(scanned)

    def current_presences(self) -> list[DeviceFoundPayload]:
        """device_found payloads for every currently-known address.

        The bus is fire-and-forget: a client connecting AFTER the first scan
        missed those events, and steady-state scans diff to silence. So the /ws
        endpoint replays these on connect — reconnect == rehydrate (invariant:
        a client never needs to replay missed events), mirroring how hello
        restates board + drivers.
        """
        out: list[DeviceFoundPayload] = []
        for addr in sorted(self._known_addrs):
            known = KNOWN_I2C_DEVICES.get(addr)
            out.append(
                DeviceFoundPayload(
                    bus="i2c",
                    addr=addr,
                    identity=known["identity"] if known else None,
                    confidence="exact" if known else "unknown",
                    suggested_spec=known["suggested_spec"] if known else None,
                )
            )
        return out

    def _diff_i2c(self, scanned: set[int]) -> None:
        """New addr -> device_found (known -> exact + suggested_spec); gone addr
        -> device_lost. Diffs against the last scan so steady state is silent."""
        for addr in sorted(scanned - self._known_addrs):
            known = KNOWN_I2C_DEVICES.get(addr)
            self._bus.publish(
                EventType.DISCOVERY_DEVICE_FOUND,
                DeviceFoundPayload(
                    bus="i2c",
                    addr=addr,
                    identity=known["identity"] if known else None,
                    confidence="exact" if known else "unknown",
                    suggested_spec=known["suggested_spec"] if known else None,
                ),
            )
        for addr in sorted(self._known_addrs - scanned):
            self._bus.publish(
                EventType.DISCOVERY_DEVICE_LOST,
                DeviceLostPayload(bus="i2c", addr=addr),
            )
        self._known_addrs = scanned

    def _classify_adc(self, pin: int, samples: list[int]) -> str:
        """Classify a u16 sample burst -> 'floating' | 'driven' | 'railed'.

        Not yet wired into the loop (I2C discovery ships first). Fingerprints:
          floating: noisy mid-scale (~32k, wide spread) — nothing attached.
          railed:   flat near 0 or 65535 — digital/ground-ish pin (wrong wire).
          driven:   near half supply, low-noise, MOVES under stimulus — real.
        """
        raise NotImplementedError("ADC presence classification is a later step")
