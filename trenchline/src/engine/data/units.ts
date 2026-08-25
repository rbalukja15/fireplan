import type { UnitClass, UnitCode } from '../types.ts'

/** The 17-unit roster dxcalc's form offers, classified the way the probe does
 * (the live select is flat; misclassifying terrain aborts a whole batch). */
export const UNIT_CLASSES: Record<UnitClass, UnitCode[]> = {
  land: ['inf', 'cav', 'ac', 'lart', 'art', 'rrg', 'lt', 'ht', 'convoy', 'st'],
  air: ['bal', 'int', 'tac', 'zep'],
  naval: ['sub', 'cl', 'bb'],
}

export const UNIT_LABELS: Record<UnitCode, string> = {
  inf: 'Infantry',
  cav: 'Cavalry',
  ac: 'Armoured Car',
  lart: 'Light Artillery',
  art: 'Artillery',
  rrg: 'Railgun',
  lt: 'Tank',
  ht: 'Heavy Tank',
  convoy: 'Airplane Convoy',
  st: 'Stormtrooper',
  bal: 'Balloon',
  int: 'Fighter',
  tac: 'Tactical Bomber',
  zep: 'Zeppelin',
  sub: 'Submarine',
  cl: 'Light Cruiser',
  bb: 'Battleship',
}

export const ALL_UNITS: UnitCode[] = [
  ...UNIT_CLASSES.land,
  ...UNIT_CLASSES.air,
  ...UNIT_CLASSES.naval,
]

export function classOf(unit: UnitCode): UnitClass {
  if (UNIT_CLASSES.air.includes(unit)) return 'air'
  if (UNIT_CLASSES.naval.includes(unit)) return 'naval'
  return 'land'
}
