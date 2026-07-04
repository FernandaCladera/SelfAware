"""Dependency dataclasses for both agents — the seam tests inject fakes through.

AuthorDeps is deliberately inert: the driver author is a pure text->schema
function, so its deps exist only to drive dynamic instructions (protocol-class
fragment + board profile). CopilotDeps carries live services, and every field
is the session/service object — NEVER a raw transport (invariant #3: only
BoardSession touches the wire).
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from selfaware.bringup.models import BringupSpec
from selfaware.config import Settings
from selfaware.events.bus import EventBus

if TYPE_CHECKING:
    from selfaware.bringup.service import CommissionService
    from selfaware.hardware.session import BoardSession
    from selfaware.memory.client import MemoryClient
    from selfaware.registry.store import DriverRegistry


@dataclass
class AuthorDeps:
    """What the author's dynamic instructions render from.

    board_profile is PRE-RENDERED text (see render_board_profile) so the
    author module never needs Settings at instruction time and tests can pass
    a literal string.
    """

    spec: BringupSpec
    board_profile: str
    few_shot: str = ""  # optional retrieved past-working driver (VectorStore, day-2)


@dataclass
class CopilotDeps:
    """Everything the dashboard copilot may touch, via tools only."""

    session: "BoardSession"
    registry: "DriverRegistry"
    bus: EventBus
    memory: "MemoryClient"
    commissioner: "CommissionService"
    settings: Settings


def render_board_profile(settings: Settings) -> str:
    """Settings pin map -> the board-constraints text block for AuthorDeps.

    One rendering, host-owned, so the prompt and the config can never state
    different pin numbers.
    """
    return (
        "# Board profile: Raspberry Pi Pico W (RP2040) on a PicoBricks mainboard\n"
        f"- ADC-capable GPIOs: {', '.join(str(p) for p in settings.adc_capable_pins)} (RP2040 physics; nothing else)\n"
        f"- I2C0: sda=GP{settings.pins_i2c_sda}, scl=GP{settings.pins_i2c_scl}\n"
        f"- Onboard bricks: pot=GP{settings.pins_pot} (ADC), ldr=GP{settings.pins_ldr} (ADC), "
        f"button=GP{settings.pins_button}, relay=GP{settings.pins_relay}, "
        f"buzzer=GP{settings.pins_buzzer} (PWM), ws2812=GP{settings.pins_ws2812}\n"
        "- 3V3 logic only. USB-CDC stdout truncates past a few hundred bytes — print nothing "
        "in the driver; the host appends the one print that matters.\n"
    )
