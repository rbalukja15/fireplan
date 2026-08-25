import { describe, expect, it } from 'vitest'
import type { Army, BattleSetup, Stack, UnitRow } from './types.ts'
import { DEFAULT_ENGINE_DATA, mergeEngineData } from './data/coefficients.ts'
import { simulate } from './simulate.ts'
import { monteCarlo } from './montecarlo.ts'
import { mulberry32 } from './formulas.ts'

function stack(partial: Partial<Stack> & { units: UnitRow[] }): Stack {
  return {
    id: partial.id ?? 's',
    terrain: partial.terrain ?? 'land',
    position: partial.position ?? 0,
    trench: partial.trench ?? 0,
    target: partial.target ?? 'defend',
    units: partial.units,
  }
}

function armies(a: Army, b: Army, maxRounds = 100): BattleSetup {
  return { armies: { A: a, B: b }, maxRounds }
}

const DATA = DEFAULT_ENGINE_DATA

function duel(atk: UnitRow[], def: UnitRow[], maxRounds = 100): BattleSetup {
  return armies(
    { stacks: [stack({ id: 'A1', target: 0, units: atk })] },
    { stacks: [stack({ id: 'B1', target: 'defend', units: def })] },
    maxRounds,
  )
}

describe('simulate', () => {
  it('is deterministic without an rng', () => {
    const setup = duel(
      [{ unit: 'inf', count: 10, hpPct: 100 }],
      [{ unit: 'inf', count: 12, hpPct: 100 }],
    )
    const r1 = simulate(setup, DATA)
    const r2 = simulate(setup, DATA)
    expect(r1).toEqual(r2)
  })

  it('mirrors when sides swap', () => {
    const atk: UnitRow[] = [{ unit: 'inf', count: 10, hpPct: 100 }]
    const def: UnitRow[] = [{ unit: 'cav', count: 4, hpPct: 100 }]
    const fwd = simulate(duel(atk, def), DATA)
    const rev = simulate(
      armies(
        { stacks: [stack({ id: 'A1', target: 'defend', units: def })] },
        { stacks: [stack({ id: 'B1', target: 0, units: atk })] },
      ),
      DATA,
    )
    expect(fwd.winner === 'A' ? 'B' : fwd.winner === 'B' ? 'A' : fwd.winner).toBe(rev.winner)
    expect(fwd.sides.A.hpLost).toBeCloseTo(rev.sides.B.hpLost, 9)
    expect(fwd.sides.B.hpLost).toBeCloseTo(rev.sides.A.hpLost, 9)
  })

  it('bigger stack of the same unit wins', () => {
    const r = simulate(
      duel(
        [{ unit: 'inf', count: 30, hpPct: 100 }],
        [{ unit: 'inf', count: 10, hpPct: 100 }],
      ),
      DATA,
    )
    expect(r.winner).toBe('A')
    expect(r.sides.B.hpAfter).toBe(0)
    expect(r.sides.A.hpAfter).toBeGreaterThan(0)
  })

  it('single round of one attacker vs a fat stack deals exactly base damage', () => {
    // probe methodology: HP delta after one round IS the base damage
    const r = simulate(
      duel(
        [{ unit: 'cav', count: 1, hpPct: 100 }],
        [{ unit: 'inf', count: 20, hpPct: 100 }],
        1,
      ),
      DATA,
    )
    expect(r.sides.B.hpLost).toBeCloseTo(DATA.units.cav.damage.value, 9)
  })

  it('applies m(f) to a damaged attacker', () => {
    const r = simulate(
      duel(
        [{ unit: 'cav', count: 1, hpPct: 50 }],
        [{ unit: 'inf', count: 20, hpPct: 100 }],
        1,
      ),
      DATA,
    )
    expect(r.sides.B.hpLost).toBeCloseTo(15 * (0.05 + 0.95 * 0.5), 9)
  })

  it('applies the E(n) size factor past 20 attackers', () => {
    const r = simulate(
      duel(
        [{ unit: 'inf', count: 50, hpPct: 100 }],
        [{ unit: 'inf', count: 200, hpPct: 100 }],
        1,
      ),
      DATA,
    )
    // 50 infantry hit as 35 effective units
    expect(r.sides.B.hpLost).toBeCloseTo(35 * 4, 6)
  })

  it('patrol quarter-ticks decide battles at fractional rounds', () => {
    const merged = mergeEngineData({ units: { tac: { damage: 80 } } })
    const r = simulate(
      armies(
        {
          stacks: [
            stack({ id: 'A1', terrain: 'patrol', target: 0, units: [{ unit: 'tac', count: 1, hpPct: 100 }] }),
          ],
        },
        { stacks: [stack({ id: 'B1', units: [{ unit: 'inf', count: 1, hpPct: 100 }] })] },
      ),
      merged,
    )
    expect(r.winner).toBe('A')
    expect(r.rounds % 1).not.toBe(0)
  })

  it('ranged units strike from beyond melee, melee units do not', () => {
    const setup = armies(
      {
        stacks: [
          stack({
            id: 'A1',
            position: 0,
            target: 0,
            units: [
              { unit: 'art', count: 2, hpPct: 100 },
              { unit: 'inf', count: 5, hpPct: 100 },
            ],
          }),
        ],
      },
      { stacks: [stack({ id: 'B1', position: 30, units: [{ unit: 'inf', count: 20, hpPct: 100 }] })] },
      1,
    )
    const r = simulate(setup, DATA)
    // only the 2 artillery reach 30 km; the infantry contribute nothing
    expect(r.sides.B.hpLost).toBeCloseTo(2 * DATA.units.art.damage.value, 6)
    expect(r.warnings.some((w) => w.includes('out of range'))).toBe(true)
    // and the defender cannot return fire at 30 km with infantry
    expect(r.sides.A.hpLost).toBe(0)
  })

  it('declares stalemate when nothing can die', () => {
    const r = simulate(
      duel(
        [{ unit: 'convoy', count: 1, hpPct: 100 }], // unknown damage -> 0
        [{ unit: 'convoy', count: 1, hpPct: 100 }],
        5,
      ),
      DATA,
    )
    expect(r.winner).toBe('stalemate')
    expect(r.warnings.some((w) => w.includes('unmeasured'))).toBe(true)
  })

  it('handles an empty side at round zero', () => {
    const r = simulate(
      duel([{ unit: 'inf', count: 10, hpPct: 100 }], []),
      DATA,
    )
    expect(r.winner).toBe('A')
    expect(r.rounds).toBe(0)
  })

  it('uses the defense figure for return fire (calibration divergence knob)', () => {
    // dxcalc's live response for this battle has the DEFENDER winning
    // (calibration/dxcalc-10inf2art-vs-12inf.html). With defense == attack our
    // engine has the attacker winning; raising infantry defense flips it,
    // proving return fire reads the defense table.
    const setup = duel(
      [
        { unit: 'inf', count: 10, hpPct: 100 },
        { unit: 'art', count: 2, hpPct: 100 },
      ],
      [{ unit: 'inf', count: 12, hpPct: 100 }],
    )
    expect(simulate(setup, DATA).winner).toBe('A')
    const buffed = mergeEngineData({ units: { inf: { defense: 8 } } })
    expect(simulate(setup, buffed).winner).toBe('B')
  })

  it('golden regression: 10 inf + 2 art vs 12 inf on land', () => {
    // Tripwire for the engine's arithmetic: update consciously, never casually.
    const r = simulate(
      duel(
        [
          { unit: 'inf', count: 10, hpPct: 100 },
          { unit: 'art', count: 2, hpPct: 100 },
        ],
        [{ unit: 'inf', count: 12, hpPct: 100 }],
      ),
      DATA,
    )
    expect(r.winner).toBe('A')
    expect(r.rounds).toBe(8)
    expect(r.sides.A.hpLost).toBeCloseTo(164.2056600495499, 6)
    expect(r.sides.B.hpLost).toBeCloseTo(240, 6)
  })
})

describe('monteCarlo', () => {
  it('is reproducible for a given seed', () => {
    const setup = duel(
      [{ unit: 'inf', count: 12, hpPct: 100 }],
      [{ unit: 'inf', count: 11, hpPct: 100 }],
    )
    const a = monteCarlo(setup, DATA, 50, 7)
    const b = monteCarlo(setup, DATA, 50, 7)
    expect(a.winProbability).toEqual(b.winProbability)
    expect(a.hpLost).toEqual(b.hpLost)
  })

  it('collapses to the deterministic result at zero variance', () => {
    const merged = mergeEngineData({ variancePct: 0 })
    const setup = duel(
      [{ unit: 'inf', count: 12, hpPct: 100 }],
      [{ unit: 'inf', count: 11, hpPct: 100 }],
    )
    const det = simulate(setup, merged)
    const mc = monteCarlo(setup, merged, 20, 99)
    expect(mc.winProbability[det.winner as 'A' | 'B']).toBeCloseTo(1, 9)
    expect(mc.hpLost.A.min).toBeCloseTo(det.sides.A.hpLost, 9)
    expect(mc.hpLost.A.max).toBeCloseTo(det.sides.A.hpLost, 9)
  })

  it('loss ranges bracket the deterministic losses', () => {
    const setup = duel(
      [{ unit: 'inf', count: 20, hpPct: 100 }],
      [{ unit: 'inf', count: 10, hpPct: 100 }],
    )
    const det = simulate(setup, DATA)
    const mc = monteCarlo(setup, DATA, 200, 1234)
    expect(mc.hpLost.A.min).toBeLessThanOrEqual(det.sides.A.hpLost + 1e-9)
    expect(mc.hpLost.A.max).toBeGreaterThanOrEqual(det.sides.A.hpLost - 1e-9)
  })

  it('variance rng actually perturbs outcomes', () => {
    // asymmetric duel: the surviving side's remaining HP is roll-sensitive
    const setup = duel(
      [{ unit: 'inf', count: 20, hpPct: 100 }],
      [{ unit: 'inf', count: 10, hpPct: 100 }],
    )
    const rng = mulberry32(5)
    const varied = simulate(setup, DATA, rng)
    const flat = simulate(setup, DATA)
    expect(varied.sides.A.hpLost).not.toBeCloseTo(flat.sides.A.hpLost, 6)
  })
})
