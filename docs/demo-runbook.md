# Demo runbook — the judge-facing five minutes

Rehearse the whole arc offline first: `make demo` (mock board + canned author
+ frontend). Nothing in the flagship path depends on wifi, API keys, or the
venue's power strips. Record a screen capture of one clean run as the
last-resort fallback.

## The beats, in order

1. **Cold open — the landing void.** One line, one looping teaser terminal,
   `> enter the console`. No feature grid, no SaaS chrome.
2. **Hotplug — the device materializes.** Plug the sensor in (or let the mock
   hotplug fire): a card appears on the DeviceRail.
   - I2C module → named card ("SHTC3 @0x70", confidence: exact) — real
     auto-detection from the bus scan.
   - Analog module → "something on GP27 — what is it?" (confidence: unknown).
     Say the honesty line out loud: *"a raw voltage physically cannot tell you
     what produced it — so we detect presence, and you teach it once."*
3. **Teach it once.** Name it / click the preset → `cmd.commission`.
4. **The flagship: fail → repair → pass on real silicon.** The stepper lights
   generate → validate → deploy → test; the TracebackPane interrupts in red
   with the board's **verbatim** error; the repair loop-back draws; attempt 2
   passes with a live reading. Narrate: *"that traceback came from the chip,
   not the model — it can't be hallucinated, and it steers the fix."*
5. **Liveness, not vibes.** Cover the LDR / wave at the ultrasonic — the scope
   moves. (Mock: `cmd.stimulate`.) *"A plausible number is not a live sensor;
   movement under stimulus is."*
6. **Capability accretion.** Open the ChatDock: "what's the light level?" →
   the copilot calls `read_ldr` — a tool that did not exist five minutes ago —
   and reports the live value. Ask about a sensor that isn't commissioned: it
   says so instead of inventing a number.
7. **The glass brain (Grafana).** Open the Commission Theater dashboard: the
   trace waterfall of the exact commission the judges just watched —
   generate/validate/deploy/test spans, the failed attempt, token usage.
8. **Close with the honesty floor.** Tractable: analog reads, self-identifying
   bus devices, single-pulse timing. Hard: multi-register state machines,
   bit-banged timing. Impossible: "auto-detect anything." Saying this is what
   makes the rest believable.

## Making the first failure deterministic (never hope for a hallucination)

- **Offline/keyless (always works):** `SELFAWARE_MOCK_BOARD=true
  SELFAWARE_MOCK_AUTHOR=true` — canned author + scripted board traceback.
- **Real board:** the gate intentionally blocks the "non-ADC pin" trick, so
  use the wrong-platform priming route (ESP32-style steering with the gate's
  `.atten` check relaxed via config for the demo run) so the **board itself**
  raises `AttributeError: 'ADC' object has no attribute 'atten'`. Decide and
  rehearse this on build day; see docs/hardware-bringup.md.
- **Physics variant:** passive buzzer driven with DC → no sound → cross-modal
  verify sees no delta → repair switches to PWM. The error is the world
  declining to change.

## Failure ladder (when hardware misbehaves under fluorescent lights)

1. Real board + real model (the plan).
2. Real board + `SELFAWARE_MOCK_AUTHOR=true` (USB works, wifi/API doesn't).
3. `make demo` fully mock (nothing works but the laptop).
4. The screen recording (nothing works at all).

Pre-demo checklist: `make infra-up` early (image pulls are slow on venue
wifi); `make test`; one full mock run; one full real run; disable the IDE's
MicroPython auto-connect (it steals the serial port — "device busy" is almost
always this); charge the laptop.
