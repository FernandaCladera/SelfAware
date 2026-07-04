"""Prompt-context models for the author. DriverGenOutput lives in
bringup/models.py (single home, invariant: agents import the domain's schema,
never define a twin) — re-exported here so agent code has one import point.

AttemptContext is the WHOLE repair context: the host rebuilds it per attempt
instead of accumulating message_history, so what the model sees is small,
flat, reproducible, and always carries the verbatim error untouched.
"""

from typing import Literal

from pydantic import BaseModel

from selfaware.bringup.models import DriverGenOutput

__all__ = ["AttemptContext", "DriverGenOutput", "FailureKind"]

FailureKind = Literal["gate_rejected", "board_traceback", "implausible", "timeout"]


class AttemptContext(BaseModel):
    """Everything the repair prompt template needs, rendered deterministically.

    verbatim_error is the gate reason OR the board's UNTOUCHED stderr —
    embedding it unedited is the loop's un-fakeable signal (invariant #1).
    """

    attempt_n: int
    previous_code: str = ""
    failure_kind: FailureKind = "board_traceback"
    verbatim_error: str = ""


def classify_failure(last_error: str) -> FailureKind:
    """Map the loop's last_error string onto the repair-prompt vocabulary.

    The CommissionRunner's author seam carries one string (deliberately —
    the seam predates this package); the prefixes below are the loop's own
    wording (bringup/loop.py), so this stays a dumb string match.
    """
    if last_error.startswith("static gate rejected"):
        return "gate_rejected"
    if last_error.startswith("host timeout"):
        return "timeout"
    if "Traceback" in last_error:
        return "board_traceback"
    return "implausible"
