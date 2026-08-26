import { useEffect, useReducer, useRef } from 'react'
import type { Action, AppState } from './store.ts'
import { initialState, migrateV1, reducer } from './store.ts'

const KEY = 'fireplan:v1'
const OLD_KEY = 'trenchline:v1' // pre-rebrand storage; read once, then superseded
const DEBOUNCE_MS = 300

export function loadPersisted(): AppState {
  try {
    const raw = localStorage.getItem(KEY) ?? localStorage.getItem(OLD_KEY)
    if (!raw) return initialState()
    const parsed = JSON.parse(raw) as { schema?: number }
    if (parsed?.schema === 2) return parsed as AppState
    if (parsed?.schema === 1) return migrateV1(parsed)
    return initialState()
  } catch {
    return initialState()
  }
}

function save(state: AppState): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(state))
  } catch {
    // storage full or blocked — the app still works, it just forgets
  }
}

/** useReducer wired to a debounced localStorage mirror. `flush` writes
 * immediately — call it before anything that may close this window (the
 * dxCalc submit closes an extension popup). */
export function usePersistentReducer(): [AppState, (a: Action) => void, () => void] {
  const [state, dispatch] = useReducer(reducer, undefined, loadPersisted)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const latest = useRef(state)
  latest.current = state

  useEffect(() => {
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(() => save(latest.current), DEBOUNCE_MS)
    return () => {
      if (timer.current) clearTimeout(timer.current)
    }
  }, [state])

  const flush = (): void => {
    if (timer.current) clearTimeout(timer.current)
    save(latest.current)
  }

  return [state, dispatch, flush]
}
