import { useEffect, useState } from 'react'
import type { BattleResult } from './engine/research.ts'
import { runBattle } from './engine/research.ts'
import { ExportGuardError, buildDxcalcPayload } from './export/dxcalcPayload.ts'
import { submitToDxcalc } from './export/dxcalcSubmit.ts'
import { usePersistentReducer } from './state/persistence.ts'
import { toBattleConfig } from './state/store.ts'
import { DispatchCtx, StateCtx } from './state/context.ts'
import { ArmyTabs } from './components/ArmyTabs.tsx'
import { BattleControls } from './components/BattleControls.tsx'
import { ReportView } from './components/ReportView.tsx'

export default function App() {
  const [state, dispatch, flush] = usePersistentReducer()
  const [result, setResult] = useState<BattleResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [updateReady, setUpdateReady] = useState(false)

  // Long-open sessions: when a deploy's fresh service worker takes over
  // (sw.js uses skipWaiting), offer a reload. First-visit controller
  // acquisition is not an update, hence the hadController guard.
  useEffect(() => {
    if (!(import.meta.env.MODE === 'web' && 'serviceWorker' in navigator)) return
    const hadController = Boolean(navigator.serviceWorker.controller)
    const onChange = (): void => {
      if (hadController) setUpdateReady(true)
    }
    navigator.serviceWorker.addEventListener('controllerchange', onChange)
    return () => navigator.serviceWorker.removeEventListener('controllerchange', onChange)
  }, [])

  const runSimulation = (): void => {
    setError(null)
    // The engine contract says simulate() never throws — it reports failure
    // through coverage instead. The try is a last line, not the design.
    try {
      setResult(runBattle(toBattleConfig(state)))
    } catch (e) {
      setResult(null)
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  // Must stay synchronous: a user-gesture form submit is what popup blockers allow.
  const sendToDxcalc = (): void => {
    setError(null)
    try {
      const payload = buildDxcalcPayload(toBattleConfig(state))
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
              <h1>Fireplan</h1>
              <p className="tagline">Supremacy 1914 · combat calculator</p>
            </div>
            <nav className="masthead-actions">
              {isPopup && (
                <a className="btn ghost" href="index.html" target="_blank" rel="noreferrer">
                  Open full tab
                </a>
              )}
            </nav>
          </header>

          <ArmyTabs />

          <BattleControls onSimulate={runSimulation} onSendToDxcalc={sendToDxcalc} />

          {error && <p className="banner error">{error}</p>}

          {result && <ReportView result={result} />}

          {updateReady && (
            <div className="update-toast" role="status">
              <span>A new version of Fireplan is ready.</span>
              <button className="btn small primary" onClick={() => window.location.reload()}>
                Reload
              </button>
            </div>
          )}

          <footer className="colophon">
            <p>
              Powered by the same replay-tested engine as the{' '}
              <a href="https://rbalukja15.github.io/fireplan/research/" target="_blank" rel="noreferrer">
                research calculator
              </a>
              : every coefficient measured by black-box probing of{' '}
              <a href="https://dxcalc.com/s1914" target="_blank" rel="noreferrer">
                dxter&rsquo;s calculator
              </a>
              . Fan-made tool — not affiliated with Bytro Labs or dxcalc.
            </p>
          </footer>
        </div>
      </DispatchCtx.Provider>
    </StateCtx.Provider>
  )
}
