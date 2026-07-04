# Protocol class: pulse_timing (trigger/echo choreography)

- Drive the trig pin: hold low ~2us, high 10us, low — use
  `time.sleep_us`, not loops.
- Time the echo with `machine.time_pulse_us(echo_pin, 1, 30000)` — the
  explicit timeout (~30ms) is MANDATORY. Without it a missing echo hangs the
  board and the host has to kill the line.
- `time_pulse_us` returns a NEGATIVE sentinel (-1/-2) on timeout. It does not
  raise. Return that negative number as-is — the host reads it as "no echo",
  which is honest and repairable; converting it to a distance would be a lie.
- Configure the echo pin as `machine.Pin(n, machine.Pin.IN, machine.Pin.PULL_DOWN)`
  — a floating echo line reads phantom pulses.
- Convert a positive pulse width to distance: `us / 58` gives centimeters for
  an HC-SR04. Return centimeters when the spec's unit is cm.
