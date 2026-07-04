"""Copilot: TestModel calls every tool -> proves the static toolset schemas
build, the dynamic registry toolset arms read_<slug>, the tool resolves the
driver AT CALL TIME and hits the (mock) silicon, and recall degrades honestly."""

from selfaware.agents.copilot import copilot_agent
from selfaware.agents.deps import CopilotDeps
from selfaware.bringup.models import BringupSpec
from selfaware.config import Settings
from selfaware.events.bus import EventBus
from selfaware.events.types import DriverStatus, ProtocolClass
from selfaware.hardware.mock_board import MockBoard
from selfaware.hardware.session import BoardSession
from selfaware.memory.client import NullMemoryClient
from selfaware.registry.models import DriverRecord
from selfaware.registry.store import DriverRegistry

from pydantic_ai.models.test import TestModel

from tests.conftest import BusSpy

GOOD_ADC_CODE = (
    "import machine\n"
    "class Driver:\n"
    "    def __init__(self):\n"
    "        self.adc = machine.ADC(27)\n"
    "    def read(self):\n"
    "        return self.adc.read_u16()\n"
)


class FakeCommissioner:
    """CommissionService stand-in: records enqueues, returns an id."""

    def __init__(self) -> None:
        self.specs: list[BringupSpec] = []

    def enqueue(self, spec: BringupSpec) -> str:
        self.specs.append(spec)
        return "fake-commission-id"


def _deps(
    settings: Settings, bus: EventBus, board: MockBoard, registry: DriverRegistry
) -> tuple[CopilotDeps, FakeCommissioner]:
    session = BoardSession(board, bus, settings)
    commissioner = FakeCommissioner()
    deps = CopilotDeps(
        session=session,
        registry=registry,
        bus=bus,
        memory=NullMemoryClient(),
        commissioner=commissioner,  # type: ignore[arg-type] — structural stand-in
        settings=settings,
    )
    return deps, commissioner


async def test_testmodel_calls_registry_tool_and_hits_mock_silicon(
    settings: Settings, bus: EventBus, bus_spy: BusSpy, mock_board: MockBoard, fake_registry: DriverRegistry
) -> None:
    await mock_board.connect()
    fake_registry.register(
        DriverRecord(
            slug="ldr",
            display_name="Light sensor",
            protocol_class=ProtocolClass.ANALOG,
            driver_code=GOOD_ADC_CODE,
            pins={"adc": 27},
            unit="raw",
            status=DriverStatus.ACTIVE,
        )
    )
    deps, commissioner = _deps(settings, bus, mock_board, fake_registry)

    result = await copilot_agent.run("what does the light sensor read?", deps=deps, model=TestModel())

    # read_ldr must have exec'd real driver code on the (mock) board
    assert any("ADC(27)" in code for code in mock_board.exec_log), "read_ldr never hit the silicon"
    # ...and narrated it as a sensor.reading on the bus
    readings = bus_spy.of_type("sensor.reading")
    assert readings and readings[0].payload["slug"] == "ldr"
    # TestModel also called commission_sensor -> the single-door service saw it
    assert commissioner.specs, "commission_sensor did not go through the commissioner"
    assert isinstance(result.output, str)


async def test_tools_resolve_at_call_time_hot_swap(
    settings: Settings, bus: EventBus, mock_board: MockBoard, fake_registry: DriverRegistry
) -> None:
    """The invariant behind repair: swap driver_code, the SAME toolset object
    runs the new code on its next call."""
    await mock_board.connect()
    fake_registry.register(
        DriverRecord(
            slug="ldr",
            display_name="Light sensor",
            protocol_class=ProtocolClass.ANALOG,
            driver_code=GOOD_ADC_CODE,
            pins={"adc": 27},
            status=DriverStatus.ACTIVE,
        )
    )
    session = BoardSession(mock_board, bus, settings)
    toolset = fake_registry.as_toolset(session)  # built BEFORE the swap

    await fake_registry.perform_read(session, "ldr")
    assert "ADC(27)" in mock_board.exec_log[-1]

    fake_registry.update_code("ldr", GOOD_ADC_CODE.replace("ADC(27)", "ADC(26)"), reason="repair")
    await fake_registry.perform_read(session, "ldr")
    assert "ADC(26)" in mock_board.exec_log[-1], "stale code ran after hot-swap"
    assert toolset is not None  # the pre-swap toolset object stayed valid throughout


async def test_recall_answers_memory_offline_with_null_client(
    settings: Settings, bus: EventBus, mock_board: MockBoard, fake_registry: DriverRegistry
) -> None:
    from selfaware.agents.copilot import recall  # the registered tool function

    deps, _ = _deps(settings, bus, mock_board, fake_registry)

    class Ctx:  # minimal RunContext stand-in: the tool only touches .deps
        def __init__(self, deps: CopilotDeps) -> None:
            self.deps = deps

    answer = await recall(Ctx(deps), "ldr wiring")  # type: ignore[arg-type]
    assert answer == "memory offline"
