"""configure_observability() + the selfaware.* span vocabulary.

Wiring: logfire SDK with send_to_logfire=False -> OTLP/HTTP :4318 -> the
grafana/otel-lgtm box. PydanticAI agent runs (GenAI semconv spans, named by
agent) nest under commission.stage{stage=generate} because the author runs
inside that span's context — that nesting is what makes the Grafana
drill-down read as a story.

Span conventions (docs/observability.md, PR5):
  commission          selfaware.slug, selfaware.protocol_class,
                      selfaware.attempts_used, selfaware.converged
  commission.attempt  + selfaware.attempt_n, selfaware.gate_verdict,
                      selfaware.board_error_class, selfaware.reading_value
  commission.stage    selfaware.stage, selfaware.attempt_n, selfaware.slug

Everything here is fail-open: configuration errors never block boot, and the
span helpers hand back a no-op handle until logfire is actually configured
(so the test suite and keyless boots stay silent).
"""

import contextlib
import os
from collections.abc import Iterator
from typing import Any

from selfaware.config import Settings

_configured = False


def configure_observability(settings: Settings, app: Any | None = None) -> None:
    """Idempotent; call FIRST in the lifespan, before any agent runs.

    Never raises: a broken/absent OTLP stack is the documented degrade path
    (exporter buffers/drops in the background).
    """
    global _configured
    os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", settings.otlp_endpoint)
    try:
        import logfire

        if not _configured:
            logfire.configure(send_to_logfire=False, service_name="selfaware-backend", console=False)
            logfire.instrument_pydantic_ai()
            _configured = True
        if app is not None:
            logfire.instrument_fastapi(app)
    except Exception:  # noqa: BLE001 — telemetry must never block boot
        return


class _NoopSpan:
    """Stands in for a logfire span when observability is unconfigured."""

    def set_attribute(self, key: str, value: Any) -> None:
        return None


@contextlib.contextmanager
def _span(name: str, **attributes: Any) -> Iterator[Any]:
    """Open a logfire span with selfaware.* attributes, or a no-op handle."""
    if not _configured:
        yield _NoopSpan()
        return
    import logfire

    with logfire.span(name, **{f"selfaware.{k}": v for k, v in attributes.items()}) as span:
        yield span


def commission_span(slug: str, protocol_class: str):
    """Wraps one whole commission. The loop stamps attempts_used/converged on
    the yielded handle via set_attribute as outcomes land."""
    return _span("commission", slug=slug, protocol_class=protocol_class)


def attempt_span(slug: str, protocol_class: str, attempt_n: int):
    """One turn of the ratchet, child of `commission`."""
    return _span("commission.attempt", slug=slug, protocol_class=protocol_class, attempt_n=attempt_n)


def stage_span(stage: str, slug: str, attempt_n: int):
    """One stage beat; the author's GenAI spans nest under stage=generate."""
    return _span("commission.stage", stage=stage, slug=slug, attempt_n=attempt_n)
