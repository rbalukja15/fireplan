import { useMemo, useState } from 'react'
import type { BattleReport as Report, BattleSetup } from './engine/types.ts'
import { mergeEngineData } from './engine/data/coefficients.ts'
import { simulate } from './engine/simulate.ts'
import { monteCarlo, type MonteCarloResult } from './engine/montecarlo.ts'
import { ExportGuardError, buildDxcalcPayload } from './export/dxcalcPayload.ts'
import { submitToDxcalc } from './export/dxcalcSubmit.ts'
import { usePersistentReducer } from './state/persistence.ts'
import { DispatchCtx, StateCtx } from './state/context.ts'
import { ArmyTabs } from './components/ArmyTabs.tsx'
import { SimControls } from './components/SimControls.tsx'
import { BattleReportView, VarianceReportView } from './components/BattleReport.tsx'
import { EngineDataPanel } from './components/EngineDataPanel.tsx'

export type SimResult =
  | { kind: 'single'; report: Report }
  | { kind: 'mc'; mc: MonteCarloResult }

export default function App() {
  const [state, dispatch, flush] = usePersistentReducer()
  const [result, setResult] = useState<SimResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [dataOpen, setDataOpen] = useState(false)

  const engineData = useMemo(
    () => mergeEngineData(state.engineOverrides),
    [state.engineOverrides],
  )

  const setup = (): BattleSetup => ({
    armies: state.armies,
    maxRounds: state.settings.maxRounds,
  })

  const runSimulation = (): void => {
    setError(null)
    try {
      if (state.settings.variance) {
        setResult({ kind: 'mc', mc: monteCarlo(setup(), engineData, state.settings.varianceRuns) })
      } else {
        setResult({ kind: 'single', report: simulate(setup(), engineData) })
      }
    } catch (e) {
      setResult(null)
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  // Must stay synchronous: a user-gesture form submit is what popup blockers allow.
  const sendToDxcalc = (): void => {
    setError(null)
    try {
      const payload = buildDxcalcPayload(setup(), { variance: state.settings.variance })
      flush()
      submitToDxcalc(payload)
    } catch (e) {
      if (e instanceof ExportGuardError) setError(e.message)
      else throw e
    }
  }

  const isPopup = document.body.classList.contains('popup')

  return (
    <StateCtx.Provider value={state}>
      <DispatchCtx.Provider value={dispatch}>
        <div className="shell">
          <header className="masthead">
            <div className="wordmark">
              <h1>Trenchline</h1>
              <p className="tagline">Supremacy 1914 · combat calculator</p>
            </div>
            <nav className="masthead-actions">
              {isPopup && (
                <a className="btn ghost" href="index.html" target="_blank" rel="noreferrer">
                  Open full tab
                </a>
              )}
              <button className="btn ghost" onClick={() => setDataOpen((v) => !v)}>
                Engine data
              </button>
            </nav>
          </header>

          {dataOpen && <EngineDataPanel data={engineData} onClose={() => setDataOpen(false)} />}

          <ArmyTabs />

          <SimControls onSimulate={runSimulation} onSendToDxcalc={sendToDxcalc} />

          {error && <p className="banner error">{error}</p>}

          {result?.kind === 'single' && <BattleReportView report={result.report} />}
          {result?.kind === 'mc' && <VarianceReportView mc={result.mc} />}

          <footer className="colophon">
            <p>
              Engine coefficients measured by black-box probing of{' '}
              <a href="https://dxcalc.com/s1914" target="_blank" rel="noreferrer">
                dxter&rsquo;s calculator
              </a>
              ; unverified values are flagged in Engine data, and the fully
              measured cross-class model lives in the{' '}
              <a href="https://rbalukja15.github.io/fireplan/research/" target="_blank" rel="noreferrer">
                research calculator
              </a>
              . Fan-made tool — not affiliated with Bytro Labs or dxcalc.
            </p>
          </footer>
        </div>
      </DispatchCtx.Provider>
    </StateCtx.Provider>
  )
}
