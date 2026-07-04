# Observability — watch the agent decide

PydanticAI + FastAPI are instrumented via the logfire SDK with
`send_to_logfire=False`, exporting OTLP to the local `grafana/otel-lgtm`
container (`SELFAWARE_OTLP_ENDPOINT`, default `http://localhost:4318`).
Fail-open by design: if the collector is down the exporter buffers and drops —
telemetry can never block boot or the loop.

```
backend ──OTLP/HTTP :4318──► otel-lgtm ──► Tempo (traces) / Loki (logs) / Prometheus
                                   └─► Grafana :3000 (dashboard auto-provisioned)
```

## Span conventions (`selfaware.*` attributes)

| Span | Parent | Attributes |
|---|---|---|
| `commission` | — | `selfaware.slug`, `selfaware.protocol_class`, `selfaware.attempts_used`, `selfaware.converged`, `selfaware.failure_reason` |
| `commission.attempt` | commission | `selfaware.attempt_n`, `selfaware.gate_verdict` (`pass` \| `fail:<check>`), `selfaware.board_error_class` (`none` \| exception name \| `timeout` \| `implausible`), `selfaware.reading_value` |
| `commission.stage` | attempt | `selfaware.stage` ∈ generate\|validate\|deploy\|test\|repair |

The PydanticAI GenAI spans (`gen_ai.*`: model, token usage, tool calls) nest
under `commission.stage{stage=generate}` because the author runs inside that
span's context — the Grafana drill-down reads as a story: commission →
attempt → stage → model call.

## Grafana

`make infra-up` starts the stack; the **SelfAware · Commission Theater**
dashboard auto-provisions from `infra/lgtm/dashboards/`. Panels: commission
trace waterfall (TraceQL `{name = "commission"}`), converged/failed,
attempts-to-converge table, verbatim-traceback logs (Loki).

## Build-day checklist (~10 min, flagged UNCONFIRMED in the skeleton)

1. Dashboard provisioning mount path: the compose mounts the provider yaml at
   both plausible roots (`/otel-lgtm/grafana/conf/provisioning/dashboards/`
   and `/etc/grafana/provisioning/dashboards/`). If the dashboard doesn't
   appear: `docker exec -it <lgtm> ls /otel-lgtm/grafana*/conf/provisioning`.
2. Datasource UIDs (`tempo`, `loki`) assumed in the dashboard JSON — check
   Grafana → Connections and fix the JSON if the image ships different UIDs.
3. TraceQL *metrics* queries need Tempo's metrics-generator; if the image has
   it off, keep the `select()` table panels (they work regardless).
4. Exact `gen_ai.*` usage-attribute namespace of the pinned pydantic-ai —
   check one real trace, then finalize the token-usage panel.
5. agent-memory-server REST paths: probe `http://localhost:8100/docs`.
