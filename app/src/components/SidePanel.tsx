import type { SideKey, UnitCode } from '../engine/research.ts'
import {
  BUILDINGS,
  BUILDING_CODES,
  HEROES,
  HERO_CODES,
  MAX_UNIT_ROWS,
  TRENCH_MAX_LEVEL,
  UNITS,
} from '../engine/research.ts'
import { freeUnits } from '../state/store.ts'
import { useAppDispatch, useAppState } from '../state/context.ts'

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
            <span>hp %</span>
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
                <input
                  type="number"
                  min={0}
                  max={500}
                  value={row.count}
                  onChange={(e) => dispatch({ type: 'setRow', side, row: r, patch: { count: Number(e.target.value) } })}
                />
                <input
                  type="number"
                  min={1}
                  max={100}
                  value={row.hpPct}
                  onChange={(e) => dispatch({ type: 'setRow', side, row: r, patch: { hpPct: Number(e.target.value) } })}
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
            <button className="btn small ghost" onClick={() => dispatch({ type: 'setHero', side, hero: { code: 'hank', level: 10, hpPct: 100 } })}>
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
              <input
                type="number"
                min={1}
                max={HEROES[s.hero.code]?.maxLevel ?? 20}
                title={`Level 1–${HEROES[s.hero.code]?.maxLevel ?? 20}`}
                value={s.hero.level}
                onChange={(e) => dispatch({ type: 'patchHero', side, patch: { level: Number(e.target.value) } })}
              />
              <input
                type="number"
                min={1}
                max={100}
                title="Hero HP %"
                value={s.hero.hpPct}
                onChange={(e) => dispatch({ type: 'patchHero', side, patch: { hpPct: Number(e.target.value) } })}
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
              <input
                type="number"
                min={1}
                max={BUILDINGS[b.code]?.maxLevel ?? 5}
                title={`Level 1–${BUILDINGS[b.code]?.maxLevel ?? 5}`}
                value={b.level}
                onChange={(e) => dispatch({ type: 'setBuilding', side, index: i, patch: { level: Number(e.target.value) } })}
              />
              <input
                type="number"
                min={1}
                max={100}
                title="Building HP %"
                value={b.hpPct}
                onChange={(e) => dispatch({ type: 'setBuilding', side, index: i, patch: { hpPct: Number(e.target.value) } })}
              />
              <button className="btn tiny danger" title="Remove building" onClick={() => dispatch({ type: 'removeBuilding', side, index: i })}>
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
            <input
              type="number"
              min={0}
              max={TRENCH_MAX_LEVEL}
              value={s.trench}
              onChange={(e) => dispatch({ type: 'setTrench', side, level: Number(e.target.value) })}
            />
          </label>
        </div>
      </article>
    </div>
  )
}
