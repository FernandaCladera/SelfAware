"""Port discovery + HOST-authored probe snippets + the known-device table.

Plug-and-detect, the honest version (docs/hardware-bringup.md):
  * I2C devices announce an ADDRESS -> true identification via
    KNOWN_I2C_DEVICES -> discovery.device_found{confidence: "exact"}.
  * A raw ADC voltage can NEVER reveal the part (information theory, not a
    missing feature) -> presence-change detection only, confidence "unknown",
    and a human names it (the "teach it once" step).

Both probe snippets are HOST-authored constants — the LLM never writes scan
code, because discovery must be deterministic (host/LLM split, invariant #2).
"""

import glob as _glob
from typing import Any


async def find_board_port(glob_pattern: str) -> str | None:
    """Resolve the stable port id for board_port='auto'.

    glob.glob(pattern) (e.g. '/dev/cu.usbmodem*' on macOS,
    '/dev/serial/by-id/*' on Linux) -> first match, or None when nothing
    enumerates. Returning None means 'no device on the OS device list' (absent —
    check the USB *data* cable / host USB before touching code); it is NOT the
    same as 'device busy', which surfaces later as a BoardConnectError from
    SerialBoard.connect() when a second owner (an IDE auto-connect) holds the
    port. The two have opposite fixes, so they stay separate signals. Never
    returns an enumerated index.
    """
    matches = sorted(_glob.glob(glob_pattern))
    return matches[0] if matches else None


# Format with .format(sda=..., scl=...). One tiny print — REPL stdout is for
# small reads only (silent truncation past a few hundred bytes on RP2040).
I2C_SCAN_SNIPPET = (
    "from machine import I2C, Pin\n"
    "print(I2C(0, sda=Pin({sda}), scl=Pin({scl})).scan())\n"
)

# Format with .format(pin=...). Prints a small sample list; the host classifies
# the signature (see DiscoveryWatcher._classify_adc) — the board just samples.
ADC_SIGNATURE_SNIPPET = (
    "from machine import ADC\n"
    "import time\n"
    "adc = ADC({pin})\n"
    "s = []\n"
    "for _ in range(8):\n"
    "    s.append(adc.read_u16())\n"
    "    time.sleep_ms(5)\n"
    "print(s)\n"
)

# addr -> identity + pre-filled BringupSpec fields (suggested_spec rides the
# discovery.device_found payload so the UI can offer one-click commission).
# Addresses are the PicoBricks bench reality; extend freely on build day.
KNOWN_I2C_DEVICES: dict[int, dict[str, Any]] = {
    0x3C: {
        "identity": "SSD1306 OLED 128x64",
        "suggested_spec": {
            "slug": "oled",
            "display_name": "OLED display (SSD1306)",
            "protocol_class": "digital_bus",
            "i2c_addr": 0x3C,
            "extra_context": "Display, not a sensor — commission as output-ish bus device (build day).",
        },
    },
    0x70: {
        "identity": "SHTC3 temperature/humidity",
        # preset_slug routes one-click commission to the canonical spec in
        # Settings.default_specs() (correct sda/scl pins, plausibility window,
        # command-based extra_context) — single source of truth, and it carries
        # the `pins` the full-spec commission path requires.
        "suggested_spec": {
            "preset_slug": "shtc3",
            "slug": "shtc3",
            "display_name": "SHTC3 temperature/humidity",
            "protocol_class": "digital_bus",
            "i2c_addr": 0x70,
            "expected_min": -10,
            "expected_max": 60,
            "unit": "degC",
            "stimulus_hint": "breathe on the sensor",
            "extra_context": "Command-based part (wakeup 0x3517, measure 0x7CA2): command WRITES, not register reads.",
        },
    },
    0x22: {
        "identity": "PicoBricks motor driver (fan)",
        # Route one-click commission to the canonical "fan" preset in
        # Settings.default_specs() (TB6612 @ 0x22 protocol, capped soft-start,
        # guaranteed set(0)) — it carries the pins the full-spec path requires.
        "suggested_spec": {
            "preset_slug": "fan",
            "slug": "fan",
            "display_name": "Cooling fan (DC motor)",
            "protocol_class": "output",
            "i2c_addr": 0x22,
        },
    },
}
