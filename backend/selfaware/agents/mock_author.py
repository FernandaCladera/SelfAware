"""Mock author — the canned fail->repair->pass storyteller. ZERO model calls.

This is what SELFAWARE_MOCK_AUTHOR=true wires into the loop's author seam, and
it pairs with hardware.mock_board.demo_fail_then_pass_script():

  attempt 1: gate-PASSING analog code that reads the WRONG (but ADC-capable)
             pin — it must clear the static gate so it reaches the "board",
             where the demo script answers with a genuine-looking verbatim
             ValueError traceback.
  attempt 2: the corrected driver on the spec's pin; the script answers a
             plausible reading, plausibility passes, the driver registers.

Together they make `make demo-mock` the full theater with no hardware and no
API key (the flagship demo must never depend on credentials). The reasoning
strings ARE the narration — they land in the UI via agent.thought.
"""

from selfaware.bringup.models import BringupSpec, DriverGenOutput
from selfaware.config import Settings

_DRIVER_TEMPLATE = """\
import machine
import time

class Driver:
    def __init__(self):
        self.adc = machine.ADC({pin})

    def read(self):
        total = 0
        for _ in range(8):
            total += self.adc.read_u16()
            time.sleep_ms(1)
        return total // 8
"""


def _wrong_pin(spec: BringupSpec, settings: Settings) -> int:
    """An ADC-capable pin that is NOT the spec's — wrong enough to fail on the
    (scripted) board, right enough to pass the static gate."""
    target = spec.pins.get("adc")
    for pin in settings.adc_capable_pins:
        if pin != target:
            return pin
    return settings.adc_capable_pins[0]  # pragma: no cover - degenerate config


def build_mock_author(settings: Settings):
    """Return a loop-seam-compatible author ((spec, attempt_n, last_error) ->
    DriverGenOutput) serving the canned two-beat sequence.

    Keyed on attempt_n, not internal state, so a re-run of the demo (or a
    re-commission) replays the same story deterministically.
    """

    async def author(spec: BringupSpec, attempt_n: int, last_error: str | None) -> DriverGenOutput:
        target = spec.pins.get("adc", settings.adc_capable_pins[0])
        if attempt_n == 1:
            pin = _wrong_pin(spec, settings)
            return DriverGenOutput(
                reasoning=(
                    f"{spec.display_name} is a plain analog device, so this is one ADC read. "
                    f"The wiring chart I have suggests the divider lands on GP{pin}; sampling "
                    "8x with 1ms spacing to average out noise."
                ),
                driver_code=_DRIVER_TEMPLATE.format(pin=pin),
                imports_used="machine, time",
            )
        return DriverGenOutput(
            reasoning=(
                "The board's traceback says that pin has no ADC capabilities — my pin guess "
                f"was wrong, not the read logic. The spec pins {spec.display_name} on "
                f"GP{target}, which IS ADC-capable on RP2040. Same averaged read, corrected pin."
                + (f" (board said: {last_error.splitlines()[-1]})" if last_error else "")
            ),
            driver_code=_DRIVER_TEMPLATE.format(pin=target),
            imports_used="machine, time",
        )

    return author
