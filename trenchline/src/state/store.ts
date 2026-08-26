import type {
  AttackerTerrain,
  BattleConfig,
  BuildingPick,
  DefenderTerrain,
  HeroPick,
  Mode,
  Row,
  SideConfig,
  SideKey,
  UnitCode,
} from '../engine/research.ts'
import {
  BUILDINGS,
  HEROES,
  MAX_UNIT_ROWS,
  ROSTER_ORDER,
  TRENCH_MAX_LEVEL,
  UNITS,
} from '../engine/research.ts'

export interface AppState {
  schema: 2
  attacker: SideConfig
  defender: SideConfig
  battle: {
    rounds: number
    fightToEnd: boolean
    mode: Mode
    terrain: AttackerTerrain
    defenderTerrain: DefenderTerrain
    distance: number
    mutual: boolean
  }
  activeSide: SideKey
}

export function toBattleConfig(s: AppState): BattleConfig {
  return { attacker: s.attacker, defender: s.defender, ...s.battle }
}

function newSide(count: number): SideConfig {
  return {
    rows: [{ unit: 'inf', count, hpPct: 100 }],
    trench: 0,
    buildings: [],
    hero: null,
  }
}

export function initialState(): AppState {
  return {
    schema: 2,
    attacker: newSide(30),
    defender: newSide(30),
    battle: {
      rounds: 1,
      fightToEnd: true,
      mode: 'strike',
      terrain: 'land',
      defenderTerrain: '',
      distance: 0,
      mutual: false,
    },
    activeSide: 'attacker',
  }
}

/** v1 persisted a multi-stack army model; carry its first stacks over. */
export function migrateV1(v1: unknown): AppState {
  const next = initialState()
  try {
    const old = v1 as {
      armies?: Record<'A' | 'B', { stacks?: Array<{ trench?: number; units?: Row[] }> }>
    }
    const port = (side: SideConfig, stack?: { trench?: number; units?: Row[] }): void => {
      if (!stack) return
      const rows = (stack.units ?? [])
        .filter((r) => r.count > 0 && UNITS[r.unit])
        .slice(0, MAX_UNIT_ROWS)
      if (rows.length) side.rows = rows.map((r) => ({ ...r }))
      side.trench = Math.min(TRENCH_MAX_LEVEL, Math.max(0, stack.trench ?? 0))
    }
    port(next.attacker, old.armies?.A?.stacks?.[0])
    port(next.defender, old.armies?.B?.stacks?.[0])
  } catch {
    // fall through to the fresh state
  }
  return next
}

export type Action =
  | { type: 'setRow'; side: SideKey; row: number; patch: Partial<Row> }
  | { type: 'addRow'; side: SideKey }
  | { type: 'removeRow'; side: SideKey; row: number }
  | { type: 'setTrench'; side: SideKey; level: number }
  | { type: 'setHero'; side: SideKey; hero: HeroPick | null }
  | { type: 'patchHero'; side: SideKey; patch: Partial<HeroPick> }
  | { type: 'addBuilding'; side: SideKey }
  | { type: 'setBuilding'; side: SideKey; index: number; patch: Partial<BuildingPick> }
  | { type: 'removeBuilding'; side: SideKey; index: number }
  | { type: 'setBattle'; patch: Partial<AppState['battle']> }
  | { type: 'setActiveSide'; side: SideKey }
  | { type: 'loadState'; state: AppState }
  | { type: 'resetAll' }

/** Duplicate unit types are server-refused, so a row change picks the first
 * code not already fielded on that side. */
export function freeUnits(side: SideConfig, exceptRow?: number): UnitCode[] {
  const used = new Set(
    side.rows.filter((_, i) => i !== exceptRow).map((r) => r.unit),
  )
  return ROSTER_ORDER.filter((u) => !used.has(u))
}

const clamp = (v: number, lo: number, hi: number): number =>
  Math.min(hi, Math.max(lo, Math.round(v) || lo))

export function reducer(state: AppState, action: Action): AppState {
  const next: AppState = structuredClone(state)
  switch (action.type) {
    case 'setRow': {
      const row = next[action.side].rows[action.row]
      if (!row) return state
      if (action.patch.unit !== undefined && UNITS[action.patch.unit]) {
        const taken = next[action.side].rows.some(
          (r, i) => i !== action.row && r.unit === action.patch.unit,
        )
        if (!taken) row.unit = action.patch.unit
      }
      if (action.patch.count !== undefined) row.count = clamp(Number(action.patch.count), 0, 500)
      if (action.patch.hpPct !== undefined) row.hpPct = clamp(Number(action.patch.hpPct), 1, 100)
      return next
    }
    case 'addRow': {
      const side = next[action.side]
      if (side.rows.length >= MAX_UNIT_ROWS) return state
      const free = freeUnits(side)
      if (!free.length) return state
      side.rows.push({ unit: free[0], count: 0, hpPct: 100 })
      return next
    }
    case 'removeRow':
      next[action.side].rows.splice(action.row, 1)
      return next
    case 'setTrench':
      next[action.side].trench = clamp(action.level, 0, TRENCH_MAX_LEVEL)
      return next
    case 'setHero':
      next[action.side].hero = action.hero
      return next
    case 'patchHero': {
      const hero = next[action.side].hero
      if (!hero) return state
      if (action.patch.code !== undefined && HEROES[action.patch.code]) {
        hero.code = action.patch.code
        hero.level = clamp(hero.level, 1, HEROES[hero.code].maxLevel || 20)
      }
      if (action.patch.level !== undefined) {
        hero.level = clamp(Number(action.patch.level), 1, HEROES[hero.code]?.maxLevel || 20)
      }
      if (action.patch.hpPct !== undefined) hero.hpPct = clamp(Number(action.patch.hpPct), 1, 100)
      return next
    }
    case 'addBuilding': {
      const side = next[action.side]
      side.buildings.push({ code: 'fortress', level: 1, hpPct: 100 })
      return next
    }
    case 'setBuilding': {
      const b = next[action.side].buildings[action.index]
      if (!b) return state
      if (action.patch.code !== undefined && BUILDINGS[action.patch.code]) {
        b.code = action.patch.code
        b.level = clamp(b.level, 1, BUILDINGS[b.code].maxLevel)
      }
      if (action.patch.level !== undefined) {
        b.level = clamp(Number(action.patch.level), 1, BUILDINGS[b.code]?.maxLevel ?? 5)
      }
      if (action.patch.hpPct !== undefined) b.hpPct = clamp(Number(action.patch.hpPct), 1, 100)
      return next
    }
    case 'removeBuilding':
      next[action.side].buildings.splice(action.index, 1)
      return next
    case 'setBattle':
      Object.assign(next.battle, action.patch)
      next.battle.rounds = Math.max(0.25, Math.min(100, Number(next.battle.rounds) || 1))
      next.battle.distance = clamp(Number(next.battle.distance), 0, 10000)
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
