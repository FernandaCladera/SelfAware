"""Copilot — the dashboard chat agent. Output is plain text (streams as
agent.message deltas); its power is the toolbelt:

  * static tools: commission_sensor / list_devices / board_status / recall —
    always present, all going through services (never the raw transport).
  * dynamic tools: read_<slug>/set_<slug> from the registry, rebuilt EVERY
    agent step (@copilot_agent.toolset) and resolved again at CALL time —
    a driver that passes mid-conversation appears as a new tool on the very
    next step; a repair hot-swaps what an existing tool runs.

Honesty floor lives in copilot_system.md and in the tools themselves: recall
answers "memory offline" when it holds the Null client, reads report board
errors verbatim, nothing ever invents a number.
"""

from typing import Any

from pydantic_ai import Agent, FunctionToolset, ModelSettings, RunContext

from selfaware.agents.deps import CopilotDeps
from selfaware.agents.prompts import load_prompt
from selfaware.bringup.models import BringupSpec, ProtocolClass
from selfaware.memory.client import NullMemoryClient

copilot_toolset: FunctionToolset[CopilotDeps] = FunctionToolset(
    id="copilot_static",
    instructions=(
        "Report ONLY what tools return. If a sense is not commissioned, say so — never invent a reading."
    ),
)


@copilot_toolset.tool
async def commission_sensor(
    ctx: RunContext[CopilotDeps],
    slug: str,
    protocol_class: ProtocolClass,
    pins: dict[str, int],
    display_name: str = "",
    notes: str = "",
) -> str:
    """Start commissioning a new sensor or actuator: the agent will write,
    deploy, and verify a driver on the live board. Returns immediately with a
    commission id; progress streams to the dashboard on its own.

    Args:
        slug: short identifier, e.g. "ldr" — becomes the read_/set_ tool name.
        protocol_class: analog | digital_bus | pulse_timing | output.
        pins: role -> GPIO number, e.g. {"adc": 27} or {"trig": 14, "echo": 15}.
        display_name: human name for the dashboard; defaults to the slug.
        notes: wiring quirks or part details worth telling the driver author.
    """
    spec = BringupSpec(
        slug=slug,
        display_name=display_name or slug,
        protocol_class=protocol_class,
        pins=pins,
        extra_context=notes,
    )
    commission_id = ctx.deps.commissioner.enqueue(spec)
    if commission_id is None:
        return "a commission is already running — one at a time; try again when it finishes"
    # Deliberately enqueue-and-return: a 4-attempt hardware loop must not sit
    # inside a chat turn. The dashboard narrates via commission.* events.
    return f"commissioning started (id {commission_id}); watch the stepper for progress"


@copilot_toolset.tool
async def list_devices(ctx: RunContext[CopilotDeps]) -> str:
    """List every commissioned device: slug, protocol class, status, last reading."""
    records = ctx.deps.registry.list()
    if not records:
        return "no devices commissioned yet"
    lines = []
    for r in records:
        reading = f", last reading {r.last_reading:g}{(' ' + r.unit) if r.unit else ''}" if r.last_reading is not None else ""
        attempts = f", passed in {r.attempts_used} attempt(s)" if r.attempts_used else ""
        lines.append(f"{r.slug}: {r.display_name} [{r.protocol_class.value}] status={r.status.value}{attempts}{reading}")
    return "\n".join(lines)


@copilot_toolset.tool
async def board_status(ctx: RunContext[CopilotDeps]) -> str:
    """Current board link: connected/disconnected, port, mock badge, busy flag."""
    status = ctx.deps.session.board_status()
    state = "connected" if status.connected else "disconnected"
    mock = " (MOCK board — simulated silicon)" if status.mock else ""
    busy = ", busy commissioning" if status.busy else ""
    port = f" on {status.port_id}" if status.port_id else ""
    return f"board {state}{port}{mock}{busy}"


@copilot_toolset.tool
async def recall(ctx: RunContext[CopilotDeps], query: str) -> str:
    """Search cross-session memory for wiring facts, past drivers, repair lessons."""
    if isinstance(ctx.deps.memory, NullMemoryClient):
        return "memory offline"  # the honest degrade — never improvise recollections
    results = await ctx.deps.memory.recall(query)
    if not results:
        return "nothing relevant in memory"
    return "\n".join(f"- {r}" for r in results)


copilot_agent: Agent[CopilotDeps, str] = Agent(
    # model deliberately omitted — resolved per run via author.resolve_model()
    deps_type=CopilotDeps,
    output_type=str,
    name="copilot",
    retries=1,
    instructions=load_prompt("copilot_system.md"),
    model_settings=ModelSettings(temperature=0.6, max_tokens=1024),
    toolsets=[copilot_toolset],
)


@copilot_agent.toolset
def commissioned_tools(ctx: RunContext[CopilotDeps]) -> Any:
    """The live capabilities, rebuilt from the registry each run step.

    per_run_step=True (the default) is the point: a driver admitted while the
    copilot is mid-conversation arms its tool on the very next step, and each
    tool re-resolves its record at call time (hot-swap, invariant #6).
    """
    return ctx.deps.registry.as_toolset(ctx.deps.session)
