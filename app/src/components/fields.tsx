import { useEffect, useRef, useState } from 'react'

/* Number entry that doesn't fight the user. The old inputs were controlled
 * type=number fields that clamped on every keystroke, which on a phone meant:
 * clearing a field snapped it back to 0, "0." lost its decimal point before
 * the next digit landed, and out-of-range digits were eaten mid-typing.
 * These are text fields with a numeric keyboard: while focused you can type
 * anything; the value commits live once it parses cleanly, and clamps only
 * on blur. */

export function useEditableText(synced: string): {
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

export const toNumber = (raw: string): number | null => {
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

