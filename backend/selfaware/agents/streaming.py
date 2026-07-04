"""PydanticAI stream events -> canonical agent.* bus events.

Uses `agent.run_stream_events()` (pinned against pydantic-ai 2.5.0) because it
ALWAYS runs to completion — `run_stream()` can skip tool calls when
output_type is str, a documented gotcha that would silently lobotomize the
copilot. The mapping lives in `_forward()`, a pure function over one event, so
tests feed synthetic event objects and assert payloads with no model anywhere.

Mapping (agent field ALWAYS set — the UI keys panels on it):
  PartStartEvent/PartDeltaEvent (text)      -> agent.message {delta, done: false}
  PartStartEvent/PartDeltaEvent (thinking)  -> agent.thought {text}
  FunctionToolCallEvent                     -> agent.tool_call {tool, args, tool_call_id}
  FunctionToolResultEvent                   -> agent.tool_result {tool, tool_call_id, ok, preview}
  AgentRunResultEvent                       -> agent.message {delta: "", done: true, usage}
  FinalResultEvent / PartEndEvent           -> (internal markers; nothing on the wire)
"""

from typing import Any

from pydantic_ai import Agent, AgentRunResultEvent
from pydantic_ai.messages import (
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    ModelMessage,
    PartDeltaEvent,
    PartStartEvent,
    TextPart,
    TextPartDelta,
    ThinkingPart,
    ThinkingPartDelta,
    ToolReturnPart,
)

from selfaware.config import Settings
from selfaware.events.bus import EventBus
from selfaware.events.payloads import (
    AgentMessagePayload,
    AgentThoughtPayload,
    AgentToolCallPayload,
    AgentToolResultPayload,
)
from selfaware.events.types import EventType

PREVIEW_CHARS = 500  # tool results are truncated for the feed; full values stay server-side


async def run_agent_streaming(
    agent: Agent[Any, Any],
    prompt: str,
    *,
    deps: Any,
    bus: EventBus,
    settings: Settings,
    agent_name: str,
    message_history: list[ModelMessage] | None = None,
) -> Any:
    """Run `agent` to completion, narrating every step onto the bus.

    Returns the final AgentRunResult so the caller can persist
    result.all_messages() for the next chat turn. Model resolution happens
    HERE, per run (invariant #7); ModelUnavailable propagates to the caller,
    which owns the system.error.
    """
    from selfaware.agents.author import resolve_model  # local: avoid import cycle at module load

    result: Any = None
    async with agent.run_stream_events(
        prompt,
        deps=deps,
        model=resolve_model(settings),
        message_history=message_history,
    ) as events:
        async for event in events:
            if isinstance(event, AgentRunResultEvent):
                result = event.result
            _forward(event, bus, agent_name)
    return result


def _forward(event: Any, bus: EventBus, agent_name: str) -> None:
    """The pure mapping: ONE stream event -> zero or one bus publish."""
    if isinstance(event, PartStartEvent):
        part = event.part
        if isinstance(part, TextPart) and part.content:
            bus.publish(
                EventType.AGENT_MESSAGE,
                AgentMessagePayload(agent=agent_name, delta=part.content, done=False),
            )
        elif isinstance(part, ThinkingPart) and part.content:
            bus.publish(EventType.AGENT_THOUGHT, AgentThoughtPayload(agent=agent_name, text=part.content))
        return

    if isinstance(event, PartDeltaEvent):
        delta = event.delta
        if isinstance(delta, TextPartDelta) and delta.content_delta:
            bus.publish(
                EventType.AGENT_MESSAGE,
                AgentMessagePayload(agent=agent_name, delta=delta.content_delta, done=False),
            )
        elif isinstance(delta, ThinkingPartDelta) and delta.content_delta:
            bus.publish(EventType.AGENT_THOUGHT, AgentThoughtPayload(agent=agent_name, text=delta.content_delta))
        return

    if isinstance(event, FunctionToolCallEvent):
        part = event.part
        try:
            args = part.args_as_dict()
        except Exception:  # noqa: BLE001 — half-streamed JSON args must not kill narration
            args = {"_raw": str(part.args)}
        bus.publish(
            EventType.AGENT_TOOL_CALL,
            AgentToolCallPayload(agent=agent_name, tool=part.tool_name, args=args, tool_call_id=part.tool_call_id),
        )
        return

    if isinstance(event, FunctionToolResultEvent):
        part = event.part  # ToolReturnPart on success, RetryPromptPart on ModelRetry
        ok = isinstance(part, ToolReturnPart)
        content = part.content if ok else getattr(part, "content", "")
        bus.publish(
            EventType.AGENT_TOOL_RESULT,
            AgentToolResultPayload(
                agent=agent_name,
                tool=part.tool_name or "",
                tool_call_id=part.tool_call_id,
                ok=ok,
                preview=str(content)[:PREVIEW_CHARS],
            ),
        )
        return

    if isinstance(event, AgentRunResultEvent):
        usage = event.result.usage
        bus.publish(
            EventType.AGENT_MESSAGE,
            AgentMessagePayload(
                agent=agent_name,
                delta="",
                done=True,
                usage={"input_tokens": usage.input_tokens or 0, "output_tokens": usage.output_tokens or 0},
            ),
        )
        return
    # FinalResultEvent, PartEndEvent, and anything a future pydantic-ai adds:
    # internal markers — deliberately nothing on the wire.
