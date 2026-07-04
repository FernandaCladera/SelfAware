"""_forward(): the pure stream-event -> agent.* mapping, no model anywhere.

Synthetic events are built from the INSTALLED pydantic-ai's real event classes
(pinned 2.x), so a version bump that changes shapes fails HERE, loudly, not
mid-demo."""

from types import SimpleNamespace

from pydantic_ai import AgentRunResultEvent
from pydantic_ai.messages import (
    FinalResultEvent,
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    PartDeltaEvent,
    PartStartEvent,
    RetryPromptPart,
    TextPart,
    TextPartDelta,
    ThinkingPart,
    ThinkingPartDelta,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.usage import RunUsage

from selfaware.agents.streaming import _forward
from selfaware.events.bus import EventBus

from tests.conftest import BusSpy


def test_text_start_and_delta_become_agent_message(bus: EventBus, bus_spy: BusSpy) -> None:
    _forward(PartStartEvent(index=0, part=TextPart(content="Hello")), bus, "copilot")
    _forward(PartDeltaEvent(index=0, delta=TextPartDelta(content_delta=" world")), bus, "copilot")

    events = bus_spy.of_type("agent.message")
    assert [e.payload["delta"] for e in events] == ["Hello", " world"]
    assert all(e.payload["agent"] == "copilot" for e in events)
    assert all(e.payload["done"] is False for e in events)


def test_thinking_becomes_agent_thought(bus: EventBus, bus_spy: BusSpy) -> None:
    _forward(PartStartEvent(index=0, part=ThinkingPart(content="hmm")), bus, "copilot")
    _forward(PartDeltaEvent(index=0, delta=ThinkingPartDelta(content_delta=" pins...")), bus, "copilot")

    events = bus_spy.of_type("agent.thought")
    assert [e.payload["text"] for e in events] == ["hmm", " pins..."]


def test_tool_call_and_result(bus: EventBus, bus_spy: BusSpy) -> None:
    call = ToolCallPart(tool_name="read_ldr", args={"n": 1}, tool_call_id="tc-1")
    _forward(FunctionToolCallEvent(part=call), bus, "copilot")
    _forward(
        FunctionToolResultEvent(
            part=ToolReturnPart(tool_name="read_ldr", content=41250.0, tool_call_id="tc-1")
        ),
        bus,
        "copilot",
    )

    calls = bus_spy.of_type("agent.tool_call")
    assert calls[0].payload == {
        "agent": "copilot",
        "tool": "read_ldr",
        "args": {"n": 1},
        "tool_call_id": "tc-1",
    }
    results = bus_spy.of_type("agent.tool_result")
    assert results[0].payload["ok"] is True
    assert results[0].payload["preview"] == "41250.0"
    assert results[0].payload["tool_call_id"] == "tc-1"


def test_retry_prompt_result_is_not_ok(bus: EventBus, bus_spy: BusSpy) -> None:
    part = RetryPromptPart(content="ldr is not commissioned", tool_name="read_ldr", tool_call_id="tc-2")
    _forward(FunctionToolResultEvent(part=part), bus, "copilot")

    results = bus_spy.of_type("agent.tool_result")
    assert results[0].payload["ok"] is False
    assert "not commissioned" in results[0].payload["preview"]


def test_long_tool_result_preview_truncates(bus: EventBus, bus_spy: BusSpy) -> None:
    part = ToolReturnPart(tool_name="read_ldr", content="x" * 2000, tool_call_id="tc-3")
    _forward(FunctionToolResultEvent(part=part), bus, "copilot")
    assert len(bus_spy.of_type("agent.tool_result")[0].payload["preview"]) == 500


def test_run_result_closes_the_turn_with_usage(bus: EventBus, bus_spy: BusSpy) -> None:
    fake_result = SimpleNamespace(usage=RunUsage(input_tokens=120, output_tokens=45))
    _forward(AgentRunResultEvent(result=fake_result), bus, "copilot")  # type: ignore[arg-type]

    events = bus_spy.of_type("agent.message")
    assert events[-1].payload["done"] is True
    assert events[-1].payload["delta"] == ""
    assert events[-1].payload["usage"] == {"input_tokens": 120, "output_tokens": 45}


def test_internal_markers_publish_nothing(bus: EventBus, bus_spy: BusSpy) -> None:
    _forward(FinalResultEvent(tool_name=None, tool_call_id=None), bus, "copilot")
    assert bus_spy.drain() == []
