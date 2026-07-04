"""The LLM roles: driver author + dashboard copilot.

Design rules this package encodes (invariant #7):
  * Agents are module-level singletons constructed WITHOUT a model. The model
    string is resolved per run from Settings (`author.resolve_model`), so
    importing this package never touches provider credentials — that is what
    makes the keyless boot and TestModel overrides trivial.
  * The author has no tools and no message_history: every attempt is one
    request whose repair context is rebuilt deterministically by the host.
  * The copilot's live tools come from the registry AT STEP TIME and resolve
    the driver AT CALL TIME — a mid-conversation repair hot-swaps behavior
    under a stable tool name.
"""

from selfaware.agents.author import ModelUnavailable, author_agent, resolve_model, write_driver
from selfaware.agents.copilot import copilot_agent
from selfaware.agents.streaming import run_agent_streaming

__all__ = [
    "ModelUnavailable",
    "author_agent",
    "copilot_agent",
    "resolve_model",
    "run_agent_streaming",
    "write_driver",
]
