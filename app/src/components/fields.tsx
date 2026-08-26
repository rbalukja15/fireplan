import { useEffect, useRef, useState } from 'react'

/* Number entry that doesn't fight the user. The old inputs were controlled
 * type=number fields that clamped on every keystroke, which on a phone meant:
 * clearing a field snapped it back to 0, "0." lost its decimal point before
 * the next digit landed, and out-of-range digits were eaten mid-typing.
 * These are text fields with a numeric keyboard: while focused you can type
 * anything; the value commits live once it parses cleanly, and clamps only
 * on blur. */

function useEditableText(synced: string): {
  text: string
  setText: (t: string) => void
  focused: React.MutableRefObject<boolean>
} {
  const [text, setText] = useState(synced)
  const focused = useRef(false)
  useEffect(() => {
    if (!focused.current) setText(synced)
  }, [synced])
  return { text, setText, focused }
}

const toNumber = (raw: string): number | null => {
  const cleaned = raw.replace(',', '.').trim()
  if (cleaned === '') return null
  const n = Number(cleaned)
  return Number.isFinite(n) ? n : null
}

export function NumField({
  value,
  min,
  max,
  integer,
  title,
  onCommit,
}: {
  value: number
  min: number
  max: number
  integer?: boolean
  title?: string
  onCommit: (v: number) => void
}) {
  const { text, setText, focused } = useEditableText(String(value))
  const clamp = (n: number): number =>
    Math.min(max, Math.max(min, integer ? Math.round(n) : n))
  return (
    <input
      type="text"
      inputMode={integer ? 'numeric' : 'decimal'}
      autoComplete="off"
      spellCheck={false}
      title={title}
      value={text}
      onFocus={() => {
        focused.current = true
      }}
      onChange={(e) => {
        setText(e.target.value)
        const n = toNumber(e.target.value)
        // commit live only when what was typed needs no correction, so the
        // field never rewrites itself under the user's thumbs
        if (n !== null && clamp(n) === n) onCommit(n)
      }}
      onBlur={() => {
        focused.current = false
        const n = toNumber(text)
        if (n === null) {
          setText(String(value)) // cleared or unparseable: restore
        } else {
          const c = clamp(n)
          onCommit(c)
          setText(String(c))
        }
      }}
    />
  )
}

/** HP entry the way the game shows it: a percentage ("85", "87.5", "85%"),
 * or an absolute HP total greater than 100, which is converted against
 * `maxPool` (the row's full-health pool). */
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
  // The settled display always carries the % suffix, so an absolute entry
  // that just got converted can never be misread as HP (403 over a 480 pool
  // becomes "83.96%", with the absolute echoed underneath).
  const { text, setText, focused } = useEditableText(`${pct}%`)
  const parse = (raw: string): number | null => {
    const isPercent = raw.trim().endsWith('%')
    const n = toNumber(raw.replace('%', ''))
    if (n === null || n <= 0) return null
    if (!isPercent && n > 100 && maxPool > 0) {
      return Math.min(100, Math.round((n / maxPool) * 10000) / 100)
    }
    return Math.min(100, n)
  }
  const absolute = maxPool > 0 ? Math.round((pct / 100) * maxPool * 10) / 10 : null
  return (
    <div className="hp-cell">
      <input
        type="text"
        inputMode="decimal"
        autoComplete="off"
        spellCheck={false}
        title={
          title ??
          'Percentage (87.5 or 87.5%), or the absolute HP total shown in game — values over 100 are converted for you.'
        }
        value={text}
        onFocus={() => {
          focused.current = true
        }}
        onChange={(e) => {
          setText(e.target.value)
          const raw = e.target.value
          const n = toNumber(raw.replace('%', ''))
          // live-commit plain in-range percentages only; absolute totals and
          // suffixed input settle on blur
          if (n !== null && n > 0 && n <= 100 && !raw.includes('%')) onCommit(n)
        }}
        onBlur={() => {
          focused.current = false
          const parsed = parse(text)
          if (parsed === null) {
            setText(`${pct}%`)
          } else {
            onCommit(parsed)
            setText(`${parsed}%`)
          }
        }}
      />
      {absolute !== null && (
        <span className="hp-echo" aria-hidden>
          {absolute} / {maxPool} hp
        </span>
      )}
    </div>
  )
}
