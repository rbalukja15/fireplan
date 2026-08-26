import type { AttackerTerrain, DefenderTerrain } from '../engine/research.ts'
import { patrolEligible } from '../engine/research.ts'
import { toBattleConfig } from '../state/store.ts'
import { useAppDispatch, useAppState } from '../state/context.ts'

const ATTACKER_TERRAINS: AttackerTerrain[] = ['land', 'sea', 'debark']
const DEFENDER_TERRAINS: DefenderTerrain[] = ['', 'land', 'air', 'sea', 'debark']

export function BattleControls({
  onSimulate,
  onSendToDxcalc,
}: {
  onSimulate: () => void
  onSendToDxcalc: () => void
}) {
  const state = useAppState()
  const dispatch = useAppDispatch()
  const { battle } = state
  const canPatrol = patrolEligible(toBattleConfig(state))

  return (
    <div className="controls">
      <label className="control">
        <span>attacker terrain</span>
        <select
          value={battle.terrain}
          onChange={(e) => dispatch({ type: 'setBattle', patch: { terrain: e.target.value as AttackerTerrain } })}
        >
          {ATTACKER_TERRAINS.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </label>
      <label className="control">
        <span>defender terrain</span>
        <select
          value={battle.defenderTerrain}
          onChange={(e) => dispatch({ type: 'setBattle', patch: { defenderTerrain: e.target.value as DefenderTerrain } })}
        >
          {DEFENDER_TERRAINS.map((t) => (
            <option key={t} value={t}>
              {t === '' ? 'same' : t}
            </option>
          ))}
        </select>
      </label>
      <label className="control">
        <span>distance km</span>
        <input
          type="number"
          min={0}
          value={battle.distance}
          onChange={(e) => dispatch({ type: 'setBattle', patch: { distance: Number(e.target.value) } })}
        />
      </label>
      <label className="control checkbox" title="Both stacks attack each other (dxcalc's B.1 vs A.1)">
        <input
          type="checkbox"
          checked={battle.mutual}
          onChange={(e) => dispatch({ type: 'setBattle', patch: { mutual: e.target.checked } })}
        />
        <span>mutual attack</span>
      </label>
      {canPatrol && (
        <label className="control checkbox" title="Air vs land only: patrol charges less of the attacker's own losses">
          <input
            type="checkbox"
            checked={battle.mode === 'patrol'}
            onChange={(e) => dispatch({ type: 'setBattle', patch: { mode: e.target.checked ? 'patrol' : 'strike' } })}
          />
          <span>patrol</span>
        </label>
      )}
      <label className="control checkbox" title="Run until one side is destroyed (or 100 rounds, the source calculator's cap)">
        <input
          type="checkbox"
          checked={battle.fightToEnd}
          onChange={(e) => dispatch({ type: 'setBattle', patch: { fightToEnd: e.target.checked } })}
        />
        <span>fight to the finish</span>
      </label>
      {!battle.fightToEnd && (
        <label className="control">
          <span>rounds</span>
          <input
            type="number"
            min={0.25}
            max={100}
            step={0.25}
            value={battle.rounds}
            onChange={(e) => dispatch({ type: 'setBattle', patch: { rounds: Number(e.target.value) } })}
          />
        </label>
      )}
      <span className="controls-spring" />
      <button className="btn primary" onClick={onSimulate}>
        Simulate
      </button>
      <button className="btn" onClick={onSendToDxcalc} title="Open this battle pre-filled on dxcalc.com">
        Send to dxCalc
      </button>
      <button
        className="btn ghost"
        onClick={() => {
          if (window.confirm('Reset both armies and all settings?')) dispatch({ type: 'resetAll' })
        }}
      >
        Reset
      </button>
    </div>
  )
}
