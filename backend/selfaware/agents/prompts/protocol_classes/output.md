# Protocol class: output (actuator: set and RETURN)

- `set(self, level)` CONFIGURES the hardware and RETURNS immediately. No
  sleeps, no ramps-in-a-loop, no "play a tune". The host owns time; a set()
  that blocks wedges the serial line.
- level 0 means OFF — genuinely off (duty 0 / pin low), because the host's
  safety path calls set(0) in a finally and assumes it latches silent/still.
- PWM outputs: `machine.PWM(machine.Pin(n))`, set `.freq(...)` once in the
  constructor and map level to `.duty_u16(...)` in set(). A passive buzzer is
  silent on steady DC — drive it with PWM near resonance (~1–4 kHz).
- Simple on/off loads (relay): `machine.Pin(n, machine.Pin.OUT)` and
  `.value(1 if level else 0)` is the whole driver.
- Treat any external driver chip as stateful: assume outputs LATCH until told
  otherwise, so set() must be idempotent and set(0) must always mean stop.
