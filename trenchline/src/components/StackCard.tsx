import type { Side, Stack, Terrain, UnitCode } from '../engine/types.ts'
import { ALL_UNITS, UNIT_LABELS } from '../engine/data/units.ts'
import { useAppDispatch, useAppState } from '../state/context.ts'

const TERRAINS: Terrain[] = ['land', 'air', 'sea', 'patrol', 'debark']
const other: Record<Side, Side> = { A: 'B', B: 'A' }

export function StackCard({ side, index, stack }: { side: Side; index: number; stack: Stack }) {
  const state = useAppState()
  const dispatch = useAppDispatch()
  const enemyStacks = state.armies[other[side]].stacks

  const set = (field: 'terrain' | 'position' | 'trench' | 'target', value: Terrain | number | 'defend') =>
    dispatch({ type: 'setStackField', side, index, field, value })

  return (
    <article className="stack">
      <header className="stack-head">
        <h3>
          Stack {side}
          {index + 1}
        </h3>
        <button
          className="btn tiny danger"
          title="Remove this stack"
          onClick={() => dispatch({ type: 'removeStack', side, index })}
        >
          ×
        </button>
      </header>

      <div className="stack-fields">
        <label>
          <span>vs</span>
          <select
            value={stack.target === 'defend' ? 'defend' : String(stack.target)}
            onChange={(e) => set('target', e.target.value === 'defend' ? 'defend' : Number(e.target.value))}
          >
            <option value="defend">Defend</option>
            {enemyStacks.map((s, i) => (
              <option key={s.id} value={i}>
                Stack {other[side]}
                {i + 1}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>terrain</span>
          <select value={stack.terrain} onChange={(e) => set('terrain', e.target.value as Terrain)}>
            {TERRAINS.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>pos km</span>
          <input
            type="number"
            value={stack.position}
            onChange={(e) => set('position', Number(e.target.value))}
          />
        </label>
        <label>
          <span>trench</span>
          <input
            type="number"
            min={0}
            max={3}
            value={stack.trench}
            onChange={(e) => set('trench', Number(e.target.value))}
          />
        </label>
      </div>

      <div className="unit-rows">
        <div className="unit-row unit-row-head" aria-hidden>
          <span>unit</span>
          <span>count</span>
          <span>hp %</span>
          <span />
        </div>
        {stack.units.map((row, r) => (
          <div className="unit-row" key={r}>
            <select
              value={row.unit}
              onChange={(e) =>
                dispatch({ type: 'setUnitRow', side, index, row: r, patch: { unit: e.target.value as UnitCode } })
              }
            >
              {ALL_UNITS.map((u) => (
                <option key={u} value={u}>
                  {UNIT_LABELS[u]}
                </option>
              ))}
            </select>
            <input
              type="number"
              min={0}
              value={row.count}
              onChange={(e) =>
                dispatch({ type: 'setUnitRow', side, index, row: r, patch: { count: Number(e.target.value) } })
              }
            />
            <input
              type="number"
              min={0}
              max={100}
              value={row.hpPct}
              onChange={(e) =>
                dispatch({ type: 'setUnitRow', side, index, row: r, patch: { hpPct: Number(e.target.value) } })
              }
            />
            <button
              className="btn tiny danger"
              title="Remove this unit row"
              onClick={() => dispatch({ type: 'removeUnitRow', side, index, row: r })}
            >
              ×
            </button>
          </div>
        ))}
      </div>
      <button className="btn small ghost" onClick={() => dispatch({ type: 'addUnitRow', side, index })}>
        + unit
      </button>
    </article>
  )
}
