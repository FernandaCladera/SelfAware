# Protocol class: digital_bus (I2C conversation)

- Bus: `machine.I2C(0, sda=machine.Pin({sda}), scl=machine.Pin({scl}))` — use
  the sda/scl pins from the spec (PicoBricks routes I2C0 on GP4/GP5). Bus id
  0 with those pins; do not invent a SoftI2C unless the spec says so.
- The device address comes from the spec (`i2c_addr`). Use it as an int.
- Know your part's dialect: register-read parts use `readfrom_mem`; COMMAND
  parts (e.g. SHTC3) need command WRITES (`writeto` with the command bytes,
  a short `time.sleep_ms`, then `readfrom`). The spec's extra context names
  the dialect when it is unusual — believe it.
- Unpack bytes with `struct.unpack` (mind endianness) and convert to the
  spec's unit before returning.
- Errno semantics when you see a traceback: ETIMEDOUT-class errors mean the
  bus/clock is stretched or wired wrong (check sda/scl); EIO/ENODEV-class
  errors mean the device NAK'd — wrong address or the part is asleep and
  needs its wakeup command first.
