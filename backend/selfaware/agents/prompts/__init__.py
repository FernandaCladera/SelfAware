"""Prompt files as package data, loaded via importlib.resources.

Prompts are .md files, not Python strings, because per-class prompt
engineering is the single biggest quality lever on build day — editing a
markdown file mid-demo-prep must never risk a syntax error in agent code.
`protocol_classes/<value>.md` filenames are EXACTLY the ProtocolClass wire
values (analog, digital_bus, pulse_timing, output) — change both together.
"""

from functools import lru_cache
from importlib import resources


@lru_cache(maxsize=None)
def load_prompt(name: str) -> str:
    """Read agents/prompts/<name> (e.g. "author_system.md",
    "protocol_classes/analog.md"). Works installed and editable; cached
    because author instructions re-render on every attempt."""
    root = resources.files(__package__)
    return (root / name).read_text(encoding="utf-8")
