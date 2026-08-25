import type { Coefficient, EngineData, Terrain, UnitCode } from '../engine/types.ts'
import type { EngineOverrides } from '../engine/data/coefficients.ts'
import { ALL_UNITS } from '../engine/data/units.ts'
import { useAppDispatch, useAppState } from '../state/context.ts'

function Badge({ c }: { c: Coefficient }) {
  return (
    <span className={`badge ${c.status}`} title={c.source}>
      {c.status}
    </span>
  )
}

function NumberCell({
  coeff,
  step,
  onChange,
}: {
  coeff: Coefficient
  step?: number
  onChange: (v: number) => void
}) {
  return (
    <td className="coeff-cell">
      <input
        type="number"
        step={step ?? 1}
        value={coeff.value}
        onChange={(e) => {
          const v = Number(e.target.value)
          if (Number.isFinite(v)) onChange(v)
        }}
      />
      <Badge c={coeff} />
    </td>
  )
}

export function EngineDataPanel({ data, onClose }: { data: EngineData; onClose: () => void }) {
  const { engineOverrides } = useAppState()
  const dispatch = useAppDispatch()

  const set = (overrides: EngineOverrides): void =>
    dispatch({ type: 'setEngineOverrides', overrides })

  const setUnit = (unit: UnitCode, key: 'damage' | 'defense' | 'maxHp' | 'rangeKm', v: number): void => {
    const next = structuredClone(engineOverrides)
    next.units = next.units ?? {}
    next.units[unit] = { ...next.units[unit], [key]: v }
    set(next)
  }

  const setTerrain = (terrain: Terrain, v: number): void => {
    const next = structuredClone(engineOverrides)
    next.terrainMultiplier = { ...next.terrainMultiplier, [terrain]: v }
    set(next)
  }

  const setGlobal = (key: 'trenchHpPerLevel' | 'variancePct' | 'meleeRangeKm', v: number): void => {
    set({ ...structuredClone(engineOverrides), [key]: v })
  }

  return (
    <section className="engine-data">
      <header className="engine-data-head">
        <h3>Engine data</h3>
        <p className="fineprint">
          Every coefficient carries its provenance: <span className="badge confirmed">confirmed</span>{' '}
          by a probe sweep, <span className="badge observed">observed</span> in game or docs, or{' '}
          <span className="badge unknown">unknown</span> — a placeholder waiting for a measurement.
          Edit any value; your overrides persist locally.
        </p>
        <div className="engine-data-actions">
          <button
            className="btn small ghost"
            onClick={() => {
              if (window.confirm('Discard all coefficient overrides?')) set({})
            }}
          >
            Reset to defaults
          </button>
          <button className="btn small" onClick={onClose}>
            Close
          </button>
        </div>
      </header>

      <div className="engine-table-wrap">
        <table className="engine-table">
          <thead>
            <tr>
              <th>Unit</th>
              <th>Attack / round</th>
              <th>Defense / round</th>
              <th>HP / unit</th>
              <th>Range km</th>
            </tr>
          </thead>
          <tbody>
            {ALL_UNITS.map((u) => {
              const unit = data.units[u]
              return (
                <tr key={u}>
                  <td className="u-name">
                    {unit.label} <span className="u-class">{unit.cls}</span>
                  </td>
                  <NumberCell coeff={unit.damage} step={0.5} onChange={(v) => setUnit(u, 'damage', v)} />
                  <NumberCell coeff={unit.defense} step={0.5} onChange={(v) => setUnit(u, 'defense', v)} />
                  <NumberCell coeff={unit.maxHp} step={5} onChange={(v) => setUnit(u, 'maxHp', v)} />
                  <NumberCell coeff={unit.rangeKm} step={5} onChange={(v) => setUnit(u, 'rangeKm', v)} />
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <div className="engine-table-wrap">
        <table className="engine-table">
          <thead>
            <tr>
              <th>Terrain multiplier</th>
              {(Object.keys(data.terrainMultiplier) as Terrain[]).map((t) => (
                <th key={t}>{t}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="u-name">damage ×</td>
              {(Object.entries(data.terrainMultiplier) as [Terrain, Coefficient][]).map(([t, c]) => (
                <NumberCell key={t} coeff={c} step={0.1} onChange={(v) => setTerrain(t, v)} />
              ))}
            </tr>
          </tbody>
        </table>
      </div>

      <div className="engine-table-wrap">
        <table className="engine-table">
          <thead>
            <tr>
              <th>Trench HP / level</th>
              <th>Variance ±</th>
              <th>Melee range km</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <NumberCell coeff={data.trenchHpPerLevel} step={10} onChange={(v) => setGlobal('trenchHpPerLevel', v)} />
              <NumberCell coeff={data.variancePct} step={0.01} onChange={(v) => setGlobal('variancePct', v)} />
              <NumberCell coeff={data.meleeRangeKm} step={1} onChange={(v) => setGlobal('meleeRangeKm', v)} />
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  )
}
