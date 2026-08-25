import type { Coefficient, EngineData, UnitCode, UnitData } from '../types.ts'
import { ALL_UNITS, UNIT_LABELS, classOf } from './units.ts'

/* Every number below is tagged with where it came from:
 *   confirmed — clean single-variable sweep by dxcalc_probe.py
 *   observed  — read off a live game or the dxcalc help page, not swept
 *   unknown   — placeholder; edit in the Engine Data panel as the probe
 *               (or your own in-game measurements) pins it down
 * The Engine Data panel edits a deep-merged copy; this file stays the
 * canonical record of what has actually been established. */

const PROBE = 'dxcalc_probe.py sweep'
const HELP = 'dxcalc help page'
const GAME = 'live-game army totals (count × HP divides cleanly)'
const TBD = 'not measured yet'

function coeff(value: number, status: Coefficient['status'], source: string): Coefficient {
  return { value, status, source }
}

/** Base damage per unit per full round. */
const DAMAGE: Partial<Record<UnitCode, Coefficient>> = {
  inf: coeff(4, 'confirmed', PROBE),
  cav: coeff(15, 'confirmed', PROBE),
  art: coeff(8, 'confirmed', PROBE),
  ht: coeff(45, 'confirmed', PROBE),
  tac: coeff(25, 'observed', 'probe: 25.0 vs infantry but 0.0 vs heavy tank — target-class rule unresolved'),
}

/** Damage per unit per round when DEFENDING (return fire). dxcalc gives
 * defenders different strength: a live response showed 12 defending inf
 * beating 10 inf + 2 art, impossible with defense == attack. Values below
 * default to the attack figure until the probe sweeps defense separately. */
const DEFENSE: Partial<Record<UnitCode, Coefficient>> = {}

/** Hit points of one healthy unit. */
const MAX_HP: Partial<Record<UnitCode, Coefficient>> = {
  cav: coeff(25, 'observed', GAME),
  ac: coeff(60, 'observed', GAME),
  lt: coeff(175, 'observed', GAME),
  ht: coeff(260, 'observed', GAME),
  st: coeff(40, 'observed', GAME),
  art: coeff(20, 'observed', GAME),
  bal: coeff(20, 'observed', GAME),
  inf: coeff(20, 'observed', 'dxcalc response: 12-inf pool reads back as 240 HP → 20 per unit'),
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
