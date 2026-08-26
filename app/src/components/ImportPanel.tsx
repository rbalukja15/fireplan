import { useEffect, useState } from 'react'
import type { SideKey } from '../engine/research.ts'
import {
  gameImportStatus,
  importCapable,
  readArmies,
  runDiscovery,
  type ImportStatus,
  type ImportedArmy,
} from '../import/armyImport.ts'
import { useAppDispatch } from '../state/context.ts'

/** Extension-only: pull armies straight out of the open game tab. Rendered
 * only when the WebExtension tab APIs exist (never in the web build). */
export function ImportPanel() {
  const dispatch = useAppDispatch()
  const [status, setStatus] = useState<ImportStatus | null>(null)
  const [armies, setArmies] = useState<ImportedArmy[] | null>(null)
  const [note, setNote] = useState<string | null>(null)
  const [report, setReport] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    let cancelled = false
    void gameImportStatus().then((s) => {
      if (!cancelled) setStatus(s)
    })
    return () => {
      cancelled = true
    }
  }, [])

  if (!importCapable()) return null

  const refresh = async (): Promise<void> => {
    setNote(null)
    setStatus(await gameImportStatus())
  }

  const fetchArmies = async (): Promise<void> => {
    if (!status?.available) return
    setBusy(true)
    setNote(null)
    setArmies(null)
    const res = await readArmies(status.tabId)
    setBusy(false)
    if (res.armies) {
      setArmies(res.armies)
      const dropped = res.armies.flatMap((a) => a.dropped)
      if (dropped.length) setNote(`Ignored unrecognised units: ${dropped.join(', ')}`)
    } else {
      setNote(res.error ?? 'Import failed.')
    }
  }

  const assign = (army: ImportedArmy, side: SideKey): void => {
    dispatch({ type: 'importSide', side, rows: army.rows, trench: army.trench })
    setNote(`Loaded “${army.name}” into the ${side === 'attacker' ? 'attacking' : 'defending'} army.`)
  }

  const discovery = async (): Promise<void> => {
    if (!status?.available) return
    setBusy(true)
    const text = await runDiscovery(status.tabId)
    setBusy(false)
    setReport(text)
    try {
      await navigator.clipboard.writeText(text)
      setNote('Structure report copied to the clipboard.')
    } catch {
      setNote('Copy the report from the box below.')
    }
  }

  return (
    <section className="import-panel">
      <div className="import-head">
        <h4 className="sub-head" style={{ margin: 0 }}>
          Import from game
        </h4>
        {status?.available ? (
          <span className="import-status ok">game tab: {status.tabTitle}</span>
        ) : (
          <span className="import-status">{status?.reason ?? 'looking for a game tab…'}</span>
        )}
        <button className="btn tiny" onClick={() => void refresh()} title="Re-check for an open game tab">
          ↻
        </button>
      </div>

      <div className="import-actions">
        <button className="btn small" disabled={!status?.available || busy} onClick={() => void fetchArmies()}>
          Read armies
        </button>
        <button
          className="btn small ghost"
          disabled={!status?.available || busy}
          onClick={() => void discovery()}
          title="Copies a bounded, redacted summary of the game page's structure — share it so the army extractor can be mapped to the real game."
        >
          Copy game structure report
        </button>
      </div>

      {armies && (
        <ul className="import-armies">
          {armies.map((a, i) => (
            <li key={i}>
              <span className="mono">
                {a.name} — {a.rows.reduce((n, r) => n + r.count, 0)} units
                {a.trench > 0 && `, trench ${a.trench}`}
              </span>
              <button className="btn tiny" onClick={() => assign(a, 'attacker')}>
                → A
              </button>
              <button className="btn tiny" onClick={() => assign(a, 'defender')}>
                → B
              </button>
            </li>
          ))}
        </ul>
      )}

      {note && <p className="fineprint import-note">{note}</p>}
      {report && <textarea className="import-report" readOnly value={report} rows={6} />}
    </section>
  )
}
