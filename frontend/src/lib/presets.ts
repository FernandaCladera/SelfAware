/**
 * One-click commission presets — mirrors backend `Settings.default_specs()`
 * slugs (config.py, docs/hardware-bringup.md). These devices do NOT
 * self-announce on the bus — outputs have no I2C address or readback, and a
 * raw ADC pin can't reveal what's attached — so discovery never surfaces a
 * PresenceCard for them. The rail offers explicit launch buttons instead;
 * clicking one sends `cmd.commission { preset_slug }`.
 *
 * Keep this list in lockstep with config.py `default_specs()`.
 */
export interface CommissionPreset {
  slug: string;
  label: string;
}

export const COMMISSION_PRESETS: CommissionPreset[] = [
  { slug: 'servo', label: 'Servo (SG90)' },
  { slug: 'buzzer', label: 'Buzzer' },
  { slug: 'fan', label: 'Fan (DC motor)' },
  { slug: 'ldr', label: 'Light (LDR)' },
  { slug: 'pot', label: 'Potentiometer' },
  { slug: 'shtc3', label: 'SHTC3 temp/hum' },
  { slug: 'ultrasonic', label: 'Ultrasonic' },
];
