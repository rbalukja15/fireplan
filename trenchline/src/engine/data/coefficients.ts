import type { Coefficient, EngineData, UnitCode, UnitData } from '../types.ts'
import { ALL_UNITS, UNIT_LABELS, classOf } from './units.ts'

/* Every number below is tagged with where it came from:
 *   confirmed — clean single-variable sweep by dxcalc_probe.py
 *   observed  — read off a live game or the dxcalc help page, not swept
 *   unknown   — placeholder; edit in the Engine Data panel as the probe
 *               (or your own in-game measurements) pins it down
 * The Engine Data panel edits a deep-merged copy; this file stays the
 * canonical record of what has actually been established. */

const HELP = 'dxcalc help page'
const TBD = 'not measured yet'

/* The atk/def/HP tables below are imported from the sibling research
 * calculator (../../../web/data.js), whose test suite replays every value
 * against results.jsonl — 168+ recorded dxcalc responses. atk and def are
 * SAME-CLASS (diagonal) coefficients: a unit fighting its own kind. Attack
 * is per-TARGET-class in reality (tac is 3.0 vs air but 30.0 vs ground), so
 * Trenchline's single-table model understates cross-class matchups; the
 * research calculator at /research/ carries the full measured matrices. */
const DIAGONAL = 'results.jsonl diagonal duels (see web/data.js)'

function coeff(value: number, status: Coefficient['status'], source: string): Coefficient {
  return { value, status, source }
}

/** Base ATTACK damage per unit per full round (same-class diagonal). */
const DAMAGE: Partial<Record<UnitCode, Coefficient>> = {
  inf: coeff(4, 'confirmed', DIAGONAL),
  cav: coeff(15, 'confirmed', DIAGONAL),
  ac: coeff(6, 'confirmed', DIAGONAL),
  lart: coeff(5, 'confirmed', DIAGONAL),
  art: coeff(8, 'confirmed', DIAGONAL),
  rrg: coeff(20, 'confirmed', DIAGONAL),
  lt: coeff(30, 'confirmed', DIAGONAL),
  ht: coeff(45, 'confirmed', DIAGONAL),
  convoy: coeff(1, 'confirmed', DIAGONAL),
  st: coeff(25, 'confirmed', DIAGONAL),
  bal: coeff(3, 'confirmed', DIAGONAL + '; measured flat 3.0 vs ground too'),
  int: coeff(20, 'confirmed', DIAGONAL + '; only 5.0 vs ground'),
  tac: coeff(3, 'confirmed', DIAGONAL + '; 30.0 vs ground — the common case'),
  zep: coeff(5, 'confirmed', DIAGONAL + '; 5.0 vs ground'),
  sub: coeff(40, 'confirmed', DIAGONAL),
  cl: coeff(10, 'confirmed', DIAGONAL),
  bb: coeff(40, 'confirmed', DIAGONAL),
}

/** DEFENSE damage per unit per round (return fire, same-class diagonal).
 * Measured separately from attack — dxcalc demonstrably treats them
 * differently (12 defending inf beat 10 inf + 2 art; see calibration/). */
const DEFENSE: Partial<Record<UnitCode, Coefficient>> = {
  inf: coeff(5, 'confirmed', DIAGONAL),
  cav: coeff(7.5, 'confirmed', DIAGONAL),
  ac: coeff(12, 'confirmed', DIAGONAL),
  lart: coeff(1, 'confirmed', DIAGONAL),
  art: coeff(2.7, 'confirmed', DIAGONAL),
  rrg: coeff(6.7, 'confirmed', DIAGONAL),
  lt: coeff(30, 'confirmed', DIAGONAL),
  ht: coeff(45, 'confirmed', DIAGONAL),
  convoy: coeff(1, 'confirmed', DIAGONAL),
  st: coeff(6.3, 'confirmed', DIAGONAL),
  bal: coeff(3, 'confirmed', DIAGONAL),
  int: coeff(20, 'confirmed', DIAGONAL),
  tac: coeff(3, 'confirmed', DIAGONAL),
  zep: coeff(5, 'confirmed', DIAGONAL),
  sub: coeff(40, 'confirmed', DIAGONAL),
  cl: coeff(10, 'confirmed', DIAGONAL),
  bb: coeff(40, 'confirmed', DIAGONAL),
}

const BRACKET = 'results.jsonl pool bracket (see web/data.js maxHPBracket)'

/** Hit points of one healthy unit. */
const MAX_HP: Partial<Record<UnitCode, Coefficient>> = {
  inf: coeff(20, 'confirmed', BRACKET),
  cav: coeff(25, 'confirmed', BRACKET),
  ac: coeff(60, 'confirmed', BRACKET),
  lart: coeff(10, 'confirmed', BRACKET),
  art: coeff(20, 'confirmed', BRACKET),
  rrg: coeff(60, 'confirmed', BRACKET),
  lt: coeff(175, 'confirmed', BRACKET),
  ht: coeff(260, 'confirmed', BRACKET),
  convoy: coeff(20, 'confirmed', BRACKET),
  st: coeff(40, 'confirmed', BRACKET),
  bal: coeff(20, 'confirmed', BRACKET),
  int: coeff(60, 'confirmed', BRACKET),
  tac: coeff(80, 'confirmed', BRACKET),
  zep: coeff(140, 'confirmed', BRACKET),
  sub: coeff(100, 'observed', BRACKET + '; no independent check'),
  cl: coeff(50, 'observed', BRACKET + '; no independent check'),
  bb: coeff(200, 'observed', BRACKET + '; no independent check'),
}

/** Attack range beyond melee, km. */
const RANGE_KM: Partial<Record<UnitCode, Coefficient>> = {
  art: coeff(50, 'observed', HELP),
  rrg: coeff(150, 'observed', HELP),
  cl: coeff(40, 'observed', HELP),
  bb: coeff(75, 'observed', HELP),
}

function unitData(unit: UnitCode): UnitData {
  const damage = DAMAGE[unit] ?? coeff(0, 'unknown', TBD)
  return {
    label: UNIT_LABELS[unit],
    cls: classOf(unit),
    damage,
    defense:
      DEFENSE[unit] ??
      coeff(damage.value, 'unknown', 'assumed equal to attack; dxcalc shows defenders differ — measure'),
    maxHp: MAX_HP[unit] ?? coeff(20, 'unknown', TBD),
    rangeKm: RANGE_KM[unit] ?? coeff(0, 'observed', 'melee-only per help page'),
  }
}

export const DEFAULT_ENGINE_DATA: EngineData = {
  units: Object.fromEntries(ALL_UNITS.map((u) => [u, unitData(u)])) as Record<UnitCode, UnitData>,
  terrainMultiplier: {
    land: coeff(1, 'confirmed', 'baseline — probe normalises on land'),
    air: coeff(1, 'unknown', TBD),
    sea: coeff(1, 'unknown', TBD),
    patrol: coeff(1, 'observed', 'probe: patrol deals 4 ticks of ¼ damage per round; extra multiplier unmeasured'),
    debark: coeff(1, 'unknown', TBD),
  },
  trenchHpPerLevel: coeff(0, 'observed', 'probe: trench levels 1–3 conferred no measurable benefit'),
  variancePct: coeff(0.1, 'observed', 'dxcalc UI: ±10% roll; distribution never sampled'),
  meleeRangeKm: coeff(5, 'observed', HELP),
}

/** Overrides persisted by the Engine Data panel: only `value` changes; the
 * status flips to 'observed' with the user as source, so reports stay honest. */
export type EngineOverrides = {
  units?: Partial<Record<UnitCode, Partial<Record<'damage' | 'defense' | 'maxHp' | 'rangeKm', number>>>>
  terrainMultiplier?: Partial<Record<keyof EngineData['terrainMultiplier'], number>>
  trenchHpPerLevel?: number
  variancePct?: number
  meleeRangeKm?: number
}

const USER = 'user override (Engine Data panel)'

export function mergeEngineData(overrides: EngineOverrides | undefined): EngineData {
  if (!overrides) return DEFAULT_ENGINE_DATA
  const merged: EngineData = structuredClone(DEFAULT_ENGINE_DATA)
  for (const [unit, fields] of Object.entries(overrides.units ?? {})) {
    const u = merged.units[unit as UnitCode]
    if (!u || !fields) continue
    for (const key of ['damage', 'defense', 'maxHp', 'rangeKm'] as const) {
      const v = fields[key]
      if (typeof v === 'number' && Number.isFinite(v)) u[key] = coeff(v, 'observed', USER)
    }
  }
  for (const [terrain, v] of Object.entries(overrides.terrainMultiplier ?? {})) {
    if (typeof v === 'number' && Number.isFinite(v)) {
      merged.terrainMultiplier[terrain as keyof EngineData['terrainMultiplier']] = coeff(v, 'observed', USER)
    }
  }
  for (const key of ['trenchHpPerLevel', 'variancePct', 'meleeRangeKm'] as const) {
    const v = overrides[key]
    if (typeof v === 'number' && Number.isFinite(v)) merged[key] = coeff(v, 'observed', USER)
  }
  return merged
}
