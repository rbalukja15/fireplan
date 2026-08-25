import { describe, expect, it } from 'vitest'
import { effectiveUnits, hpMultiplier, mulberry32 } from './formulas.ts'

describe('effectiveUnits E(n)', () => {
  it('is identity up to 20', () => {
    expect(effectiveUnits(1)).toBe(1)
    expect(effectiveUnits(7)).toBe(7)
    expect(effectiveUnits(20)).toBe(20)
  })

  it('follows the probe quadratic past 20', () => {
    expect(effectiveUnits(21)).toBeCloseTo(20 + (1 * 59) / 60, 12)
    expect(effectiveUnits(30)).toBeCloseTo(20 + (10 * 50) / 60, 12)
  })

  it('caps at exactly 35 effective units from 50', () => {
    expect(effectiveUnits(50)).toBe(35)
    expect(effectiveUnits(51)).toBe(35)
    expect(effectiveUnits(120)).toBe(35)
  })

  it('is monotone non-decreasing over 1..50', () => {
    for (let n = 2; n <= 50; n++) {
      expect(effectiveUnits(n)).toBeGreaterThanOrEqual(effectiveUnits(n - 1))
    }
  })

  it('handles zero and negatives', () => {
    expect(effectiveUnits(0)).toBe(0)
    expect(effectiveUnits(-3)).toBe(0)
  })
})

describe('hpMultiplier m(f)', () => {
  it('matches the exact probe fit at the endpoints', () => {
    expect(hpMultiplier(0)).toBeCloseTo(0.05, 12)
    expect(hpMultiplier(1)).toBeCloseTo(1, 12)
  })

  it('is linear in between', () => {
    expect(hpMultiplier(0.5)).toBeCloseTo(0.525, 12)
    for (const f of [0.1, 0.33, 0.77]) {
      expect(hpMultiplier(f)).toBeCloseTo(0.05 + 0.95 * f, 12)
    }
  })

  it('clamps out-of-range fractions', () => {
    expect(hpMultiplier(-1)).toBeCloseTo(0.05, 12)
    expect(hpMultiplier(2)).toBeCloseTo(1, 12)
  })
})

describe('mulberry32', () => {
  it('is deterministic per seed and stays in [0,1)', () => {
    const a = mulberry32(42)
    const b = mulberry32(42)
    for (let i = 0; i < 100; i++) {
      const v = a()
      expect(v).toBe(b())
      expect(v).toBeGreaterThanOrEqual(0)
      expect(v).toBeLessThan(1)
    }
  })
})
