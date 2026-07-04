/**
 * DeviceRail — the living inventory. PresenceCards ("unidentified presence —
 * commission?") surface discovery.* hits; DriverCards are commissioned
 * drivers with read/set affordances. Callbacks are wired by Console to
 * getTransport().send().
 */

import type { DriverCard, PresenceCard } from '../../types/domain';
import { COMMISSION_PRESETS, type CommissionPreset } from '../../lib/presets';

export interface DeviceRailProps {
  drivers: DriverCard[];
  presences: PresenceCard[];
  onRead: (slug: string) => void;
  onSet: (slug: string, level: number) => void;
  onCommission: (presence: PresenceCard) => void;
  /** Launch a preset commission (device that doesn't self-announce, e.g. servo). */
  onCommissionPreset: (slug: string) => void;
  presets?: CommissionPreset[];
}

const CLASS_GLYPH: Record<DriverCard['protocolClass'], string> = {
  analog: '∿',
  digital_bus: '⎍',
  pulse_timing: '⟟',
  output: '⏻',
};

export function DeviceRail({
  drivers,
  presences,
  onRead,
  onSet,
  onCommission,
  onCommissionPreset,
  presets = COMMISSION_PRESETS,
}: DeviceRailProps) {
  const active = new Set(drivers.map((d) => d.slug));

  return (
    <div className="rail">
      <div className="rail__presets">
        <div className="rail__presets-label machine">commission a preset</div>
        <div className="rail__presets-btns">
          {presets.map((p) => (
            <button
              key={p.slug}
              type="button"
              className="btn"
              title={active.has(p.slug) ? `${p.slug} already commissioned — re-runs the loop` : `commission ${p.slug}`}
              onClick={() => onCommissionPreset(p.slug)}
            >
              {active.has(p.slug) ? '↻ ' : '+ '}
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {drivers.length === 0 && presences.length === 0 ? (
        <div className="rail__empty machine">nothing on the bus yet — plug something in, or pick a preset above</div>
      ) : null}

      {presences.map((p) => (
        <div key={p.key} className="card card--presence">
          <div className="card__title machine">
            {p.identity ?? 'unidentified presence'}
          </div>
          <div className="card__meta machine">
            {p.bus === 'i2c' ? `i2c 0x${(p.addr ?? 0).toString(16)}` : `adc GP${p.pin ?? '?'}`}
            {' · '}
            {p.confidence === 'exact' ? 'known device' : 'something is there'}
          </div>
          <button type="button" className="btn" onClick={() => onCommission(p)}>
            commission?
          </button>
        </div>
      ))}

      {drivers.map((d) => (
        <div key={d.slug} className={`card card--driver card--${d.status}`}>
          <div className="card__title machine">
            <span className="card__glyph">{CLASS_GLYPH[d.protocolClass]}</span> {d.displayName}
          </div>
          <div className="card__meta machine">
            {d.slug} · {d.protocolClass}
            {d.status === 'repairing' ? ' · repairing…' : ''}
          </div>
          <div className="card__reading machine">
            {d.lastReading !== undefined ? `${d.lastReading} ${d.unit}` : '—'}
          </div>
          <div className="card__actions">
            <button type="button" className="btn" onClick={() => onRead(d.slug)}>
              read
            </button>
            {d.protocolClass === 'output' ? (
              <>
                <button type="button" className="btn" onClick={() => onSet(d.slug, 1)}>
                  set 1
                </button>
                <button type="button" className="btn" onClick={() => onSet(d.slug, 0)}>
                  set 0
                </button>
              </>
            ) : null}
          </div>
        </div>
      ))}
    </div>
  );
}
