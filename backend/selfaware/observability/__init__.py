"""Spans and logs to local Grafana LGTM — always fail-open.

Telemetry is a witness, never a dependency: configure_observability() wraps
everything in try/except, span helpers degrade to no-ops when logfire never
configured, and a down OTLP endpoint just drops exports in the background.
The suite runs with observability unconfigured and must stay silent.
"""
