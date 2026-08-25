export type UnitClass = 'land' | 'air' | 'naval'

export type UnitCode =
  | 'inf' | 'cav' | 'ac' | 'lart' | 'art' | 'rrg' | 'lt' | 'ht' | 'convoy' | 'st'
  | 'bal' | 'int' | 'tac' | 'zep'
  | 'sub' | 'cl' | 'bb'

export type Terrain = 'land' | 'air' | 'sea' | 'patrol' | 'debark'

export type Side = 'A' | 'B'

/** Provenance of a number: measured by the probe, read off a live game, or a
 * placeholder awaiting measurement. The engine uses `value` either way — the
 * status exists so the UI and reports can say how much to trust a result. */
export type CoefficientStatus = 'confirmed' | 'observed' | 'unknown'

export interface Coefficient {
  value: number
  status: CoefficientStatus
  source: string
}

export interface UnitData {
  label: string
  cls: UnitClass
  /** Base damage per unit per full round when attacking. */
  damage: Coefficient
  /** Base damage per unit per full round when defending (return fire).
   * S1914 units defend with different strength than they attack — a live
   * dxcalc battle showed 12 defending infantry beating 10 inf + 2 art,
   * which equal attack/defense values cannot reproduce. */
  defense: Coefficient
  /** Hit points of one healthy unit. */
  maxHp: Coefficient
  /** Attack range in km beyond melee; 0 = melee-only. */
  rangeKm: Coefficient
}

export interface EngineData {
  units: Record<UnitCode, UnitData>
  terrainMultiplier: Record<Terrain, Coefficient>
  /** Extra defender HP pool per trench level. */
  trenchHpPerLevel: Coefficient
  /** Half-width of the damage roll when variance is on (0.10 = ±10%). */
  variancePct: Coefficient
  meleeRangeKm: Coefficient
}

export interface UnitRow {
  unit: UnitCode
  count: number
  /** 0–100. */
  hpPct: number
}

export interface Stack {
  id: string
  terrain: Terrain
  /** Position along a line, km. */
  position: number
  /** 0–3. */
  trench: number
  /** 'defend', or the index of the enemy stack this one attacks. */
  target: 'defend' | number
  units: UnitRow[]
}

export interface Army {
  stacks: Stack[]
}

export interface BattleSetup {
  armies: Record<Side, Army>
  /** Whole rounds; the simulation steps in quarter-round ticks. */
  maxRounds: number
}

export interface UnitReport {
  unit: UnitCode
  countBefore: number
  countAfter: number
  hpBefore: number
  hpAfter: number
  died: number
}

export interface StackReport {
  id: string
  units: UnitReport[]
  hpBefore: number
  hpAfter: number
}

export interface SideReport {
  stacks: StackReport[]
  hpBefore: number
  hpAfter: number
  hpLost: number
}

export interface BattleReport {
  winner: Side | 'draw' | 'stalemate'
  /** Quarter-round precision (a patrol tick can decide a battle at 9.25). */
  rounds: number
  sides: Record<Side, SideReport>
  warnings: string[]
}
