import { useAppDispatch, useAppState } from '../state/context.ts'

export function SimControls({
  onSimulate,
  onSendToDxcalc,
}: {
  onSimulate: () => void
  onSendToDxcalc: () => void
}) {
  const { settings } = useAppState()
  const dispatch = useAppDispatch()
  return (
    <div className="controls">
      <label className="control">
        <span>max rounds</span>
        <input
          type="number"
          min={1}
          max={1000}
          value={settings.maxRounds}
          onChange={(e) => dispatch({ type: 'setSettings', patch: { maxRounds: Number(e.target.value) } })}
        />
      </label>
      <label className="control checkbox">
        <input
          type="checkbox"
          checked={settings.variance}
          onChange={(e) => dispatch({ type: 'setSettings', patch: { variance: e.target.checked } })}
        />
        <span>±10% variance</span>
      </label>
      {settings.variance && (
        <label className="control">
          <span>runs</span>
          <input
            type="number"
            min={10}
            max={2000}
            value={settings.varianceRuns}
            onChange={(e) => dispatch({ type: 'setSettings', patch: { varianceRuns: Number(e.target.value) } })}
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
