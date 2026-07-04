"""Mock author: the canned two-beat story — both beats must clear the real
static gate (a mock that the gate rejects would deadlock the keyless demo)."""

from selfaware.agents.mock_author import build_mock_author
from selfaware.bringup.gate import run_gate
from selfaware.bringup.models import BringupSpec, ProtocolClass
from selfaware.config import Settings


def _spec(settings: Settings) -> BringupSpec:
    return BringupSpec(
        slug="ldr",
        display_name="Light sensor (LDR)",
        protocol_class=ProtocolClass.ANALOG,
        pins={"adc": settings.pins_ldr},
        expected_min=0,
        expected_max=65535,
        unit="raw",
    )


async def test_attempts_differ_and_both_pass_the_gate(settings: Settings) -> None:
    author = build_mock_author(settings)
    spec = _spec(settings)

    first = await author(spec, 1, None)
    second = await author(spec, 2, "ValueError: Pin GP15 does not have ADC capabilities")

    assert first.driver_code != second.driver_code
    for gen in (first, second):
        gate = run_gate(gen.driver_code, spec, settings, imports_used=gen.imports_used)
        assert gate.passed, gate.reason


async def test_story_beats(settings: Settings) -> None:
    """Attempt 1 reads the WRONG (but ADC-capable) pin; attempt 2 reads the
    spec's pin and its reasoning references the board's error."""
    author = build_mock_author(settings)
    spec = _spec(settings)

    first = await author(spec, 1, None)
    assert f"ADC({settings.pins_ldr})" not in first.driver_code  # wrong pin on purpose

    second = await author(spec, 2, "ValueError: Pin GP15 does not have ADC capabilities")
    assert f"ADC({settings.pins_ldr})" in second.driver_code  # corrected
    assert "traceback" in second.reasoning.lower() or "pin" in second.reasoning.lower()


async def test_deterministic_replay(settings: Settings) -> None:
    """Keyed on attempt_n, not hidden state: a demo re-run replays identically."""
    author = build_mock_author(settings)
    spec = _spec(settings)
    a = await author(spec, 1, None)
    b = await author(spec, 1, None)
    assert a.driver_code == b.driver_code
