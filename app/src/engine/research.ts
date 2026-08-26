/* The one engine. Fireplan used to carry its own simplified combat model;
 * it is gone. This adapter wraps the research calculator's engine
 * (../../web/engine.js) — the clean-room implementation whose test suite
 * replays every value against results.jsonl — so heroes, buildings, trench
 * schedules, cross-class matrices, patrol, embarkation and the coverage
 * contract all come from the same replay-tested source the /research/ app
 * uses. This file only adds types and the config plumbing. */

// eslint-disable-next-line @typescript-eslint/ban-ts-comment
// @ts-ignore — plain JS module, typed here at the seam
import * as ENGINE from '../../../web/engine.js'
// @ts-ignore — plain JS module, typed here at the seam
import * as DATA from '../../../web/data.js'

export type UnitCode =
  | 'inf' | 'cav' | 'ac' | 'lart' | 'art' | 'rrg' | 'lt' | 'ht' | 'convoy' | 'st'
  | 'bal' | 'int' | 'tac' | 'zep'
  | 'sub' | 'cl' | 'bb'

export type AttackerTerrain = 'land' | 'sea' | 'debark'
export type DefenderTerrain = '' | 'land' | 'air' | 'sea' | 'debark'
export type Mode = 'strike' | 'patrol'
export type SideKey = 'attacker' | 'defender'

export interface Row {
  unit: UnitCode
  count: number
  hpPct: number
}

export interface HeroPick {
  code: string
  level: number
  hpPct: number
}

export interface BuildingPick {
  code: string
  level: number
  hpPct: number
}

export interface SideConfig {
  rows: Row[]
  trench: number
  buildings: BuildingPick[]
  hero: HeroPick | null
}

export interface BattleConfig {
  attacker: SideConfig
  defender: SideConfig
  /** Whole rounds when fightToEnd is off. */
  rounds: number
  fightToEnd: boolean
  mode: Mode
  terrain: AttackerTerrain
  /** '' = same as the attacker's. */
  defenderTerrain: DefenderTerrain
  distance: number
  mutual: boolean
}

export interface BuildingResult {
  code: string
  label?: string
  level?: number
  hpFull?: number
  hp?: number
  hpLost?: number
  destroyed?: boolean
  mitigates?: boolean
  [k: string]: unknown
}

export interface SideResult {
  pool: number | null
  hpLost: number | null
  pctLost: number | null
  deaths: number | null
  unitsLeft: number | null
  damageDealt: number | null
  wiped: boolean
  outputRaw: number | null
  damageToBuildings: number | null
  buildings: BuildingResult[]
}

export interface Coverage {
  level: 'measured' | 'estimated' | 'unknown'
  reason: string
  caveats: string[]
}

export interface DerivationStep {
  label: string
  formula: string
  value: number | null
}

export interface BattleResult {
  attacker: SideResult
  defender: SideResult
  coverage: Coverage
  derivation: DerivationStep[]
  rounds?: { decided: boolean; fought: number }
}

/** The source calculator's own default cap; the engine stops at a wipe. */
export const FIGHT_OUT_ROUNDS = 100

export function runBattle(cfg: BattleConfig): BattleResult {
  const config: Record<string, unknown> = {
    attacker: cloneSide(cfg.attacker),
    defender: cloneSide(cfg.defender),
    rounds: cfg.fightToEnd ? FIGHT_OUT_ROUNDS : cfg.rounds,
    mode: cfg.mode,
    terrain: cfg.terrain,
    distance: cfg.distance,
  }
  // Omitted rather than empty: '' would read as a fourth terrain.
  if (cfg.defenderTerrain) config.defenderTerrain = cfg.defenderTerrain
  if (cfg.mutual) config.mutual = true
  return (ENGINE as { simulate: (c: unknown) => BattleResult }).simulate(config)
}

function cloneSide(s: SideConfig) {
  return {
    rows: s.rows
      .filter((r) => r.count > 0)
      .map((r) => ({ unit: r.unit, count: r.count, hpPct: r.hpPct })),
    trench: s.trench,
    buildings: s.buildings.map((b) => ({ code: b.code, level: b.level, hpPct: b.hpPct })),
    hero: s.hero ? { code: s.hero.code, level: s.hero.level, hpPct: s.hero.hpPct } : null,
  }
}

/* ---- data the UI needs, re-exported with types ------------------------- */

interface UnitDef {
  code: UnitCode
  label: string
  cls: 'land' | 'air' | 'sea'
}

interface HeroDef {
  label: string
  maxLevel: number
  pool: number
}

interface BuildingDef {
  code: string
  label: string
  maxLevel: number
  mitigates: boolean
}

const D = DATA as {
  UNITS: Record<UnitCode, UnitDef>
  ROSTER_ORDER: UnitCode[]
  HEROES: Record<string, HeroDef>
  HEROES_OTHER_TERRAIN: Record<string, HeroDef>
  BUILDINGS: Record<string, BuildingDef>
  TRENCH_MAX_LEVEL: number
  MAX_UNIT_ROWS: number
  VARIANCE_BAND: { lo: number; hi: number; rolls: string }
}

export const UNITS = D.UNITS
export const ROSTER_ORDER = D.ROSTER_ORDER
export const BUILDINGS = D.BUILDINGS
export const TRENCH_MAX_LEVEL = D.TRENCH_MAX_LEVEL
export const MAX_UNIT_ROWS = D.MAX_UNIT_ROWS
export const VARIANCE_BAND = D.VARIANCE_BAND

/** Measured land heroes plus the air/naval ones (the engine's coverage
 * machinery explains what is and isn't measured about the latter). */
export const HEROES: Record<string, HeroDef> = { ...D.HEROES, ...D.HEROES_OTHER_TERRAIN }

export const HERO_CODES: string[] = Object.keys(HEROES)
export const BUILDING_CODES: string[] = Object.keys(BUILDINGS)

export function heroDef(code: string): HeroDef | null {
  return HEROES[code] ?? null
}

/* Re-exported closed forms, for tests and future UI hints. */
export const effectiveUnits = (ENGINE as { effectiveUnits: (n: number) => number }).effectiveUnits
export const hpMultiplier = (ENGINE as { hpMultiplier: (f: number) => number }).hpMultiplier

export function unitLabel(u: UnitCode): string {
  return UNITS[u]?.label ?? u
}

/** Patrol is only a mode when every attacker row is air (and no balloon —
 * the server aborts on bal-in-air) and every defender row is land. Mirrors
 * the research app's eligibility rule. */
export function patrolEligible(cfg: BattleConfig): boolean {
  const a = cfg.attacker.rows.filter((r) => r.count > 0)
  const d = cfg.defender.rows.filter((r) => r.count > 0)
  return (
    a.length > 0 &&
    d.length > 0 &&
    a.every((r) => UNITS[r.unit]?.cls === 'air') &&
    !a.some((r) => r.unit === 'bal') &&
    d.every((r) => UNITS[r.unit]?.cls === 'land')
  )
}
