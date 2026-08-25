import { createContext, useContext } from 'react'
import type { Action, AppState } from './store.ts'
import { initialState } from './store.ts'

export const StateCtx = createContext<AppState>(initialState())
export const DispatchCtx = createContext<(a: Action) => void>(() => {})

export function useAppState(): AppState {
  return useContext(StateCtx)
}

export function useAppDispatch(): (a: Action) => void {
  return useContext(DispatchCtx)
}
