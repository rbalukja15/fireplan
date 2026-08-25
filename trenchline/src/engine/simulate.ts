import type {
  BattleReport,
  BattleSetup,
  EngineData,
  Side,
  SideReport,
  Stack,
  StackReport,
  UnitCode,
} from './types.ts'
import { effectiveUnits, hpMultiplier } from './formulas.ts'

/* Simulation model. Confirmed pieces (dxcalc_probe.py): E(n) stack scaling,
 * m(f) HP multiplier, per-unit base damage, patrol = 4 ticks of ¼ damage per
 * round, trench as extra defender HP. Documented assumptions the probe has
 * not yet measured — each is a place a sweep could prove this engine wrong:
 *   - damage exchange is simultaneous within a tick;
 *   - incoming damage spreads over a stack's unit types (and trench pool)
 *     proportionally to their share of current total HP;
 *   - E(n)/n is applied uniformly across a stack's types;
 *   - a defending stack returns fire at its engagers, split proportionally
 *     to the damage each engager dealt it this tick;
 *   - a unit type contributes only when its range (melee 5 km, or its
 *     ranged reach) covers the distance to the engaged stack. */

interface LiveType {
  unit: UnitCode
  count: number
  hp: number
  maxPerUnit: number
  countBefore: number
  hpBefore: number
}

interface LiveStack {
  side: Side
  index: number
  src: Stack
  types: LiveType[]
  trenchHp: number
}

const QUARTERS_PER_ROUND = 4

function buildLive(side: Side, stacks: Stack[], data: EngineData): LiveStack[] {
  return stacks.map((src, index) => {
    const types: LiveType[] = src.units
      .filter((u) => u.count > 0)
      .map((u) => {
        const maxPerUnit = data.units[u.unit].maxHp.value
        const hp = u.count * maxPerUnit * (Math.min(100, Math.max(0, u.hpPct)) / 100)
        return { unit: u.unit, count: u.count, hp, maxPerUnit, countBefore: u.count, hpBefore: hp }
      })
    return {
      side,
      index,
      src,
      types,
      trenchHp: src.trench * data.trenchHpPerLevel.value,
    }
  })
}

function stackHp(s: LiveStack): number {
  return s.types.reduce((sum, t) => sum + t.hp, 0) + s.trenchHp
}

function sideAlive(stacks: LiveStack[]): boolean {
  return stacks.some((s) => stackHp(s) > 0)
}

/** Damage a stack puts out against a target `distance` km away, before any
 * variance roll. `tickFraction` is ¼ on patrol ticks, 1 on whole rounds.
 * `role` picks the attack or defense figure — dxcalc demonstrably treats
 * them differently (see coefficients.ts). */
function outgoingDamage(
  s: LiveStack,
  distance: number,
  tickFraction: number,
  role: 'attack' | 'defense',
  data: EngineData,
  warnings: Set<string>,
): number {
  const melee = data.meleeRangeKm.value
  const n = s.types.reduce((sum, t) => sum + t.count, 0)
  if (n === 0) return 0
  const scale = effectiveUnits(n) / n
  let raw = 0
  for (const t of s.types) {
    if (t.count === 0 || t.hp <= 0) continue
    const unit = data.units[t.unit]
    const reach = Math.max(melee, unit.rangeKm.value)
    if (distance > reach) {
      warnings.add(`${unit.label} out of range (${distance} km > ${reach} km) — contributed nothing`)
      continue
    }
    const strength = role === 'attack' ? unit.damage : unit.defense
    if (strength.status === 'unknown') {
      warnings.add(
        `${unit.label} ${role} damage is unmeasured (using ${strength.value}) — set it in Engine Data`,
      )
    }
    const fraction = t.hp / (t.count * t.maxPerUnit)
    raw += strength.value * t.count * hpMultiplier(fraction)
  }
  const terrain = data.terrainMultiplier[s.src.terrain]
  if (terrain.status === 'unknown' && terrain.value === 1 && s.src.terrain !== 'land') {
    warnings.add(`terrain '${s.src.terrain}' multiplier is unmeasured (using 1.0)`)
  }
  return raw * scale * terrain.value * tickFraction
}

function applyDamage(s: LiveStack, amount: number): void {
  const total = stackHp(s)
  if (total <= 0 || amount <= 0) return
  const dealt = Math.min(amount, total)
  const trenchShare = s.trenchHp / total
  s.trenchHp = Math.max(0, s.trenchHp - dealt * trenchShare)
  for (const t of s.types) {
    if (t.hp <= 0) continue
    const share = t.hp / total
    t.hp = Math.max(0, t.hp - dealt * share)
    t.count = t.hp <= 0 ? 0 : Math.min(t.count, Math.ceil(t.hp / t.maxPerUnit))
  }
}

function reportStack(s: LiveStack): StackReport {
  return {
    id: s.src.id,
    units: s.types.map((t) => ({
      unit: t.unit,
      countBefore: t.countBefore,
      countAfter: t.count,
      hpBefore: t.hpBefore,
      hpAfter: t.hp,
      died: t.countBefore - t.count,
    })),
    hpBefore: s.types.reduce((sum, t) => sum + t.hpBefore, 0),
    hpAfter: s.types.reduce((sum, t) => sum + t.hp, 0),
  }
}

function reportSide(stacks: LiveStack[]): SideReport {
  const reports = stacks.map(reportStack)
  const hpBefore = reports.reduce((sum, r) => sum + r.hpBefore, 0)
  const hpAfter = reports.reduce((sum, r) => sum + r.hpAfter, 0)
  return { stacks: reports, hpBefore, hpAfter, hpLost: hpBefore - hpAfter }
}

export function simulate(
  setup: BattleSetup,
  data: EngineData,
  rng?: () => number,
): BattleReport {
  const warnings = new Set<string>()
  const live: Record<Side, LiveStack[]> = {
    A: buildLive('A', setup.armies.A.stacks, data),
    B: buildLive('B', setup.armies.B.stacks, data),
  }
  const other: Record<Side, Side> = { A: 'B', B: 'A' }
  const maxQuarters = Math.max(1, Math.round(setup.maxRounds * QUARTERS_PER_ROUND))

  let rounds = 0
  let winner: BattleReport['winner'] = 'stalemate'

  if (!sideAlive(live.A) || !sideAlive(live.B)) {
    winner = !sideAlive(live.A) && !sideAlive(live.B) ? 'draw' : !sideAlive(live.B) ? 'A' : 'B'
    warnings.add('one side had no hit points to begin with')
    return finish(winner, 0)
  }

  const roll = (): number =>
    rng ? 1 + (rng() * 2 - 1) * data.variancePct.value : 1

  for (let q = 1; q <= maxQuarters; q++) {
    // damage is computed from a snapshot, then applied — simultaneous exchange
    const pending = new Map<LiveStack, number>()
    const incomingByAttacker = new Map<LiveStack, Map<LiveStack, number>>()
    const add = (target: LiveStack, from: LiveStack, dmg: number): void => {
      if (dmg <= 0) return
      pending.set(target, (pending.get(target) ?? 0) + dmg)
      const perAttacker = incomingByAttacker.get(target) ?? new Map<LiveStack, number>()
      perAttacker.set(from, (perAttacker.get(from) ?? 0) + dmg)
      incomingByAttacker.set(target, perAttacker)
    }

    // pass 1: stacks with explicit targets fire
    for (const side of ['A', 'B'] as const) {
      for (const s of live[side]) {
        if (stackHp(s) <= 0 || s.src.target === 'defend') continue
        const tickFraction = tickFractionFor(s, q)
        if (tickFraction === 0) continue
        const target = live[other[side]][s.src.target]
        if (!target || stackHp(target) <= 0) continue
        const distance = Math.abs(s.src.position - target.src.position)
        add(target, s, outgoingDamage(s, distance, tickFraction, 'attack', data, warnings) * roll())
      }
    }

    // pass 2: defending stacks return fire, split by incoming share
    for (const side of ['A', 'B'] as const) {
      for (const s of live[side]) {
        if (stackHp(s) <= 0 || s.src.target !== 'defend') continue
        const tickFraction = tickFractionFor(s, q)
        if (tickFraction === 0) continue
        const engagers = incomingByAttacker.get(s)
        if (!engagers || engagers.size === 0) continue
        const totalIncoming = [...engagers.values()].reduce((a, b) => a + b, 0)
        if (totalIncoming <= 0) continue
        for (const [engager, dealt] of engagers) {
          const distance = Math.abs(s.src.position - engager.src.position)
          const dmg = outgoingDamage(s, distance, tickFraction, 'defense', data, warnings) * roll()
          add(engager, s, (dmg * dealt) / totalIncoming)
        }
      }
    }

    for (const [target, dmg] of pending) applyDamage(target, dmg)

    const aAlive = sideAlive(live.A)
    const bAlive = sideAlive(live.B)
    if (!aAlive || !bAlive) {
      rounds = q / QUARTERS_PER_ROUND
      winner = !aAlive && !bAlive ? 'draw' : aAlive ? 'A' : 'B'
      return finish(winner, rounds)
    }
  }

  return finish('stalemate', maxQuarters / QUARTERS_PER_ROUND)

  function finish(w: BattleReport['winner'], r: number): BattleReport {
    return {
      winner: w,
      rounds: r,
      sides: { A: reportSide(live.A), B: reportSide(live.B) },
      warnings: [...warnings],
    }
  }
}

/** Patrol stacks act every quarter tick at ¼ strength; everything else acts
 * on whole rounds only (probe: “4 ticks of ¼ damage per round”). */
function tickFractionFor(s: LiveStack, quarter: number): number {
  if (s.src.terrain === 'patrol') return 1 / QUARTERS_PER_ROUND
  return quarter % QUARTERS_PER_ROUND === 0 ? 1 : 0
}
