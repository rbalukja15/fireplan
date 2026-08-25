import type { Army, Side, Stack, Terrain, UnitCode, UnitRow } from '../engine/types.ts'
import type { EngineOverrides } from '../engine/data/coefficients.ts'

export interface Settings {
  maxRounds: number
  variance: boolean
  varianceRuns: number
}

export interface AppState {
  schema: 1
  armies: Record<Side, Army>
  settings: Settings
  engineOverrides: EngineOverrides
  activeSide: Side
}

let nextId = 1
export function freshId(): string {
  return `s${Date.now().toString(36)}${(nextId++).toString(36)}`
}

export function newStack(target: Stack['target']): Stack {
  return {
    id: freshId(),
    terrain: 'land',
    position: 0,
    trench: 0,
    target,
    units: [{ unit: 'inf', count: 10, hpPct: 100 }],
  }
}

export function initialState(): AppState {
  return {
    schema: 1,
    armies: {
      A: { stacks: [newStack(0)] },
      B: { stacks: [newStack('defend')] },
    },
    settings: { maxRounds: 100, variance: false, varianceRuns: 200 },
    engineOverrides: {},
    activeSide: 'A',
  }
}

export type Action =
  | { type: 'addStack'; side: Side }
  | { type: 'removeStack'; side: Side; index: number }
  | { type: 'setStackField'; side: Side; index: number; field: 'terrain' | 'position' | 'trench' | 'target'; value: Terrain | number | 'defend' }
  | { type: 'addUnitRow'; side: Side; index: number }
  | { type: 'removeUnitRow'; side: Side; index: number; row: number }
  | { type: 'setUnitRow'; side: Side; index: number; row: number; patch: Partial<UnitRow> }
  | { type: 'setSettings'; patch: Partial<Settings> }
  | { type: 'setEngineOverrides'; overrides: EngineOverrides }
  | { type: 'setActiveSide'; side: Side }
  | { type: 'loadState'; state: AppState }
  | { type: 'resetAll' }

const other: Record<Side, Side> = { A: 'B', B: 'A' }

/** Any target index pointing past the enemy's stack list falls back to defend. */
function clampTargets(state: AppState): AppState {
  for (const side of ['A', 'B'] as const) {
    const enemyCount = state.armies[other[side]].stacks.length
    for (const stack of state.armies[side].stacks) {
      if (stack.target !== 'defend' && stack.target >= enemyCount) {
        stack.target = enemyCount > 0 ? 0 : 'defend'
      }
    }
  }
  return state
}

export function reducer(state: AppState, action: Action): AppState {
  const next: AppState = structuredClone(state)
  switch (action.type) {
    case 'addStack': {
      const enemyHasStacks = next.armies[other[action.side]].stacks.length > 0
      next.armies[action.side].stacks.push(newStack(enemyHasStacks ? 0 : 'defend'))
      return next
    }
    case 'removeStack':
      next.armies[action.side].stacks.splice(action.index, 1)
      return clampTargets(next)
    case 'setStackField': {
      const stack = next.armies[action.side].stacks[action.index]
      if (!stack) return state
      switch (action.field) {
        case 'terrain':
          stack.terrain = action.value as Terrain
          break
        case 'position':
          stack.position = Number(action.value) || 0
          break
        case 'trench':
          stack.trench = Math.max(0, Math.min(3, Number(action.value) || 0))
          break
        case 'target':
          stack.target = action.value === 'defend' ? 'defend' : Number(action.value)
          break
      }
      return next
    }
    case 'addUnitRow': {
      const stack = next.armies[action.side].stacks[action.index]
      if (!stack) return state
      stack.units.push({ unit: 'inf', count: 0, hpPct: 100 })
      return next
    }
    case 'removeUnitRow': {
      const stack = next.armies[action.side].stacks[action.index]
      if (!stack) return state
      stack.units.splice(action.row, 1)
      return next
    }
    case 'setUnitRow': {
      const stack = next.armies[action.side].stacks[action.index]
      const row = stack?.units[action.row]
      if (!row) return state
      if (action.patch.unit !== undefined) row.unit = action.patch.unit as UnitCode
      if (action.patch.count !== undefined) row.count = Math.max(0, Math.floor(Number(action.patch.count) || 0))
      if (action.patch.hpPct !== undefined) row.hpPct = Math.max(0, Math.min(100, Number(action.patch.hpPct) || 0))
      return next
    }
    case 'setSettings':
      Object.assign(next.settings, action.patch)
      next.settings.maxRounds = Math.max(1, Math.min(1000, Math.floor(next.settings.maxRounds) || 100))
      next.settings.varianceRuns = Math.max(10, Math.min(2000, Math.floor(next.settings.varianceRuns) || 200))
      return next
    case 'setEngineOverrides':
      next.engineOverrides = action.overrides
      return next
    case 'setActiveSide':
      next.activeSide = action.side
      return next
    case 'loadState':
      return action.state
    case 'resetAll':
      return initialState()
  }
}
