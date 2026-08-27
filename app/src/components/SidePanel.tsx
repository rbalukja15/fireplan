import type { SideKey, UnitCode } from '../engine/research.ts'
import {
  BUILDINGS,
  BUILDING_CODES,
  HEROES,
  HERO_CODES,
  MAX_UNIT_ROWS,
  TRENCH_MAX_LEVEL,
  UNITS,
  buildingPool,
  rowMaxPool,
} from '../engine/research.ts'
import { freeUnits } from '../state/store.ts'
import { useAppDispatch, useAppState } from '../state/context.ts'
import { NumField } from './fields.tsx'
import { HpField } from './hpfield.tsx'

export function SidePanel({ side, label }: { side: SideKey; label: string }) {
  const state = useAppState()
  const dispatch = useAppDispatch()
  const s = state[side]

  return (
    <div className="army">
      <div className="army-head">
        <h2>
          <span className="army-letter">{side === 'attacker' ? 'A' : 'B'}</span> {label}
        </h2>
      </div>

      <article className="stack">
        <div className="unit-rows">
          <div className="unit-row unit-row-head" aria-hidden>
            <span>unit</span>
            <span>count</span>
            <span>hp</span>
            <span />
          </div>
          {s.rows.map((row, r) => {
            const options = [row.unit, ...freeUnits(s, r).filter((u) => u !== row.unit)]
            return (
              <div className="unit-row" key={r}>
                <select
                  value={row.unit}
                  onChange={(e) =>
                    dispatch({ type: 'setRow', side, row: r, patch: { unit: e.target.value as UnitCode } })
                  }
                >
                  {options.map((u) => (
                    <option key={u} value={u}>
                      {UNITS[u].label}
                    </option>
                  ))}
                </select>
                <NumField
                  value={row.count}
                  min={0}
                  max={5000}
                  integer
                  title="Unit count"
                  onCommit={(count) => dispatch({ type: 'setRow', side, row: r, patch: { count } })}
                />
                <HpField
                  pct={row.hpPct}
                  maxPool={rowMaxPool(row.unit, row.count)}
                  onCommit={(hpPct) => dispatch({ type: 'setRow', side, row: r, patch: { hpPct } })}
                />
                <button
                  className="btn tiny danger"
                  title="Remove this unit row"
                  onClick={() => dispatch({ type: 'removeRow', side, row: r })}
                >
                  ×
                </button>
              </div>
            )
          })}
        </div>
        {s.rows.length < MAX_UNIT_ROWS && freeUnits(s).length > 0 && (
          <button className="btn small ghost" onClick={() => dispatch({ type: 'addRow', side })}>
            + unit
          </button>
        )}

        <div className="sub-block">
          <h4 className="sub-head">Hero</h4>
          {!s.hero ? (
            <button
              className="btn small ghost"
              onClick={() => dispatch({ type: 'setHero', side, hero: { code: 'hank', level: 10, hpPct: 100 } })}
            >
              + hero
            </button>
          ) : (
            <div className="unit-row hero-row">
              <select
                value={s.hero.code}
                onChange={(e) => dispatch({ type: 'patchHero', side, patch: { code: e.target.value } })}
              >
                {HERO_CODES.map((h) => (
                  <option key={h} value={h}>
                    {HEROES[h].label}
                  </option>
                ))}
              </select>
              <NumField
                value={s.hero.level}
                min={1}
                max={HEROES[s.hero.code]?.maxLevel ?? 20}
                integer
                title={`Level 1–${HEROES[s.hero.code]?.maxLevel ?? 20}`}
                onCommit={(level) => dispatch({ type: 'patchHero', side, patch: { level } })}
              />
              <HpField
                pct={s.hero.hpPct}
                maxPool={HEROES[s.hero.code]?.pool ?? 0}
                onCommit={(hpPct) => dispatch({ type: 'patchHero', side, patch: { hpPct } })}
              />
              <button className="btn tiny danger" title="Remove hero" onClick={() => dispatch({ type: 'setHero', side, hero: null })}>
                ×
              </button>
            </div>
          )}
        </div>

        <div className="sub-block">
          <h4 className="sub-head">Buildings</h4>
          {s.buildings.map((b, i) => (
            <div className="unit-row" key={i}>
              <select
                value={b.code}
                onChange={(e) => dispatch({ type: 'setBuilding', side, index: i, patch: { code: e.target.value } })}
              >
                {BUILDING_CODES.map((c) => (
                  <option key={c} value={c}>
                    {BUILDINGS[c].label}
                  </option>
                ))}
              </select>
              <NumField
                value={b.level}
                min={1}
                max={BUILDINGS[b.code]?.maxLevel ?? 5}
                integer
                title={`Level 1–${BUILDINGS[b.code]?.maxLevel ?? 5}`}
                onCommit={(level) => dispatch({ type: 'setBuilding', side, index: i, patch: { level } })}
              />
              <HpField
                pct={b.hpPct}
                maxPool={buildingPool(b.code, b.level)}
                onCommit={(hpPct) => dispatch({ type: 'setBuilding', side, index: i, patch: { hpPct } })}
              />
              <button
                className="btn tiny danger"
                title="Remove building"
                onClick={() => dispatch({ type: 'removeBuilding', side, index: i })}
              >
                ×
              </button>
            </div>
          ))}
          <button className="btn small ghost" onClick={() => dispatch({ type: 'addBuilding', side })}>
            + building
          </button>
        </div>

        <div className="sub-block trench-block">
          <label>
            <span>trench level (0–{TRENCH_MAX_LEVEL})</span>
            <NumField
              value={s.trench}
              min={0}
              max={TRENCH_MAX_LEVEL}
              integer
              onCommit={(level) => dispatch({ type: 'setTrench', side, level })}
            />
          </label>
        </div>
      </article>
    </div>
  )
}
