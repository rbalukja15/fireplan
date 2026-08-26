import { describe, expect, it } from 'vitest'
import type { BattleConfig, Row, SideConfig } from './research.ts'
import {
  BUILDINGS,
  HEROES,
  ROSTER_ORDER,
  TRENCH_MAX_LEVEL,
  effectiveUnits,
  hpMultiplier,
  patrolEligible,
  runBattle,
} from './research.ts'

function side(rows: Row[], extra: Partial<SideConfig> = {}): SideConfig {
  return { rows, trench: 0, buildings: [], hero: null, ...extra }
}

function battle(attacker: SideConfig, defender: SideConfig, extra: Partial<BattleConfig> = {}): BattleConfig {
  return {
    attacker,
    defender,
    rounds: 1,
    fightToEnd: true,
    mode: 'strike',
    terrain: 'land',
    defenderTerrain: '',
    distance: 0,
    mutual: false,
    ...extra,
  }
}

describe('re-exported closed forms', () => {
  it('E(n): identity to 20, quadratic past it, cap at 35', () => {
    expect(effectiveUnits(20)).toBe(20)
    expect(effectiveUnits(21)).toBeCloseTo(20 + (1 * 59) / 60, 12)
    expect(effectiveUnits(50)).toBe(35)
    expect(effectiveUnits(120)).toBe(35)
  })

  it('m(f): the exact probe fit', () => {
    expect(hpMultiplier(0)).toBeCloseTo(0.05, 12)
    expect(hpMultiplier(0.5)).toBeCloseTo(0.525, 12)
    expect(hpMultiplier(1)).toBeCloseTo(1, 12)
  })
})

describe('data surface', () => {
  it('serves the full roster, both hero tables, and buildings', () => {
    expect(ROSTER_ORDER).toHaveLength(17)
    expect(Object.keys(HEROES).length).toBe(22)
    expect(Object.keys(BUILDINGS)).toContain('fortress')
    expect(TRENCH_MAX_LEVEL).toBe(20)
  })
})

describe('runBattle', () => {
  it('golden: reproduces the live dxcalc calibration response', () => {
    // calibration/dxcalc-10inf2art-vs-12inf.html: attacker wiped (−240.0),
    // defender lost 175.9 of 240, decided in round ≤ 9. The engine agrees to
    // the print precision of the source page.
    const r = runBattle(
      battle(
        side([
          { unit: 'inf', count: 10, hpPct: 100 },
          { unit: 'art', count: 2, hpPct: 100 },
        ]),
        side([{ unit: 'inf', count: 12, hpPct: 100 }]),
      ),
    )
    expect(r.attacker.wiped).toBe(true)
    expect(r.attacker.hpLost).toBeCloseTo(240, 1)
    expect(r.defender.hpLost ?? 0).toBeCloseTo(175.9, 0.5)
    expect(r.rounds?.decided).toBe(true)
    expect(r.defender.wiped).toBe(false)
  })

  it('trench follows the measured staircase: ×1.00 through level 3, ×1.240 at 10', () => {
    const at = (trench: number) =>
      runBattle(
        battle(
          side([{ unit: 'inf', count: 10, hpPct: 100 }]),
          side([{ unit: 'inf', count: 10, hpPct: 100 }], { trench }),
          { rounds: 1, fightToEnd: false },
        ),
      ).defender.pool ?? 0
    // levels 1–3 measured at exactly no effect — the probe's original finding
    expect(at(3)).toBeCloseTo(at(0), 6)
    expect(at(10)).toBeCloseTo(at(0) * 1.24, 1)
  })

  it('a fortress mitigates incoming damage', () => {
    const open = runBattle(
      battle(side([{ unit: 'inf', count: 30, hpPct: 100 }]), side([{ unit: 'inf', count: 30, hpPct: 100 }]), { rounds: 1, fightToEnd: false }),
    )
    const forted = runBattle(
      battle(
        side([{ unit: 'inf', count: 30, hpPct: 100 }]),
        side([{ unit: 'inf', count: 30, hpPct: 100 }], {
          buildings: [{ code: 'fortress', level: 5, hpPct: 100 }],
        }),
        { rounds: 1, fightToEnd: false },
      ),
    )
    expect(forted.defender.hpLost ?? 0).toBeLessThan(open.defender.hpLost ?? 0)
  })

  it('a hero changes the exchange', () => {
    const cfg = () =>
      battle(side([{ unit: 'inf', count: 20, hpPct: 100 }]), side([{ unit: 'inf', count: 20, hpPct: 100 }]), {
        rounds: 1,
        fightToEnd: false,
      })
    const plain = runBattle(cfg())
    const led = runBattle({ ...cfg(), attacker: { ...cfg().attacker, hero: { code: 'hank', level: 10, hpPct: 100 } } })
    expect(led.defender.hpLost ?? 0).toBeGreaterThan(plain.defender.hpLost ?? 0)
  })

  it('never throws — a failing config comes back as unknown coverage', () => {
    const r = runBattle(
      battle(side([]), side([]), { terrain: 'land' }),
    )
    expect(r.coverage.level).toBeDefined()
    expect(Array.isArray(r.coverage.caveats)).toBe(true)
  })

  it('patrol eligibility mirrors the measured rule', () => {
    const air = side([{ unit: 'tac', count: 2, hpPct: 100 }])
    const land = side([{ unit: 'inf', count: 10, hpPct: 100 }])
    expect(patrolEligible(battle(air, land))).toBe(true)
    expect(patrolEligible(battle(land, land))).toBe(false)
    const withBal = side([
      { unit: 'tac', count: 2, hpPct: 100 },
      { unit: 'bal', count: 1, hpPct: 100 },
    ])
    expect(patrolEligible(battle(withBal, land))).toBe(false)
  })
})
