import { useState } from 'react'
import { toNumber, useEditableText } from './fields.tsx'

/** HP entry with an EXPLICIT unit: a %/hp toggle sits on the field, so the
 * interpretation is never guessed silently. In % mode the number is a
 * percentage; in hp mode it is the absolute HP total against `maxPool`
 * (stored as a percentage either way). Typing a plain value over 100 in
 * % mode flips the toggle to hp visibly and reads it as an absolute; a
 * trailing % always forces percent. The echo underneath shows the other
 * reading, and the last-used unit becomes the default for new fields. */

type HpMode = '%' | 'hp'
const HP_MODE_KEY = 'fireplan:hpmode'

function defaultHpMode(): HpMode {
  try {
    return localStorage.getItem(HP_MODE_KEY) === 'hp' ? 'hp' : '%'
  } catch {
    return '%'
  }
}

function rememberHpMode(mode: HpMode): void {
  try {
    localStorage.setItem(HP_MODE_KEY, mode)
  } catch {
    /* per-viewer convenience only */
  }
}

const round1 = (n: number): number => Math.round(n * 10) / 10
const round2 = (n: number): number => Math.round(n * 100) / 100

export function HpField({
  pct,
  maxPool,
  title,
  onCommit,
}: {
  pct: number
  maxPool: number
  title?: string
  onCommit: (pct: number) => void
}) {
  const [mode, setMode] = useState<HpMode>(defaultHpMode)
  const effMode: HpMode = maxPool > 0 ? mode : '%'
  const absOf = (p: number): number => round1((p / 100) * maxPool)
  const synced = effMode === 'hp' ? String(absOf(pct)) : String(pct)
  const { text, setText, focused } = useEditableText(synced)

  const toPct = (n: number, m: HpMode): number =>
    round2(Math.min(100, m === 'hp' && maxPool > 0 ? (n / maxPool) * 100 : n))

  const switchMode = (next: HpMode): void => {
    if (next === mode || maxPool <= 0) return
    setMode(next)
    rememberHpMode(next)
    setText(next === 'hp' ? String(absOf(pct)) : String(pct))
  }

  return (
    <div className="hp-cell">
      <div className="hp-row">
        <input
          type="text"
          inputMode="decimal"
          autoComplete="off"
          spellCheck={false}
          title={
            title ??
            (effMode === 'hp'
              ? `Absolute HP total (of ${maxPool}). Flip the toggle for percent.`
              : 'Percentage of full health. Flip the toggle to enter absolute HP; a plain value over 100 flips it for you.')
          }
          value={text}
          onFocus={() => {
            focused.current = true
          }}
          onChange={(e) => {
            setText(e.target.value)
            const raw = e.target.value
            if (raw.includes('%')) return // suffixed input settles on blur
            const n = toNumber(raw)
            if (n === null || n <= 0) return
            // live-commit only values that need no correction in this unit
            const inRange = effMode === 'hp' ? n <= maxPool : n <= 100
            if (inRange) onCommit(toPct(n, effMode))
          }}
          onBlur={() => {
            focused.current = false
            const forcedPercent = text.trim().endsWith('%')
            const n = toNumber(text.replace('%', ''))
            if (n === null || n <= 0) {
              setText(synced) // cleared or unparseable: restore
              return
            }
            let unit: HpMode = forcedPercent ? '%' : effMode
            // an over-100 plain value in % mode is an absolute: flip VISIBLY
            if (!forcedPercent && unit === '%' && n > 100 && maxPool > 0) unit = 'hp'
            if (unit !== mode && maxPool > 0) {
              setMode(unit)
              rememberHpMode(unit)
            }
            const committed = toPct(n, unit)
            onCommit(committed)
            setText(unit === 'hp' ? String(round1(Math.min(n, maxPool))) : String(committed))
          }}
        />
        <button
          type="button"
          className="hp-mode"
          disabled={maxPool <= 0}
          title={
            effMode === 'hp'
              ? 'Reading absolute HP — switch to percent'
              : 'Reading percent — switch to absolute HP'
          }
          onClick={() => switchMode(effMode === '%' ? 'hp' : '%')}
        >
          {effMode}
        </button>
      </div>
      {maxPool > 0 && (
        <span className="hp-echo" aria-hidden>
          {effMode === 'hp' ? `= ${pct}%` : `${absOf(pct)} / ${maxPool} hp`}
        </span>
      )}
    </div>
  )
}
