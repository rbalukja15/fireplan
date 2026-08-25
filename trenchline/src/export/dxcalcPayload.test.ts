import { describe, expect, it } from 'vitest'
import type { BattleSetup } from '../engine/types.ts'
import { ExportGuardError, buildDxcalcPayload } from './dxcalcPayload.ts'

const SETUP: BattleSetup = {
  maxRounds: 10,
  armies: {
    A: {
      stacks: [
        {
          id: 'A1',
          terrain: 'land',
          position: 0,
          trench: 0,
          target: 0,
          units: [
            { unit: 'inf', count: 10, hpPct: 100 },
            { unit: 'art', count: 2, hpPct: 75 },
          ],
        },
      ],
    },
    B: {
      stacks: [
        {
          id: 'B1',
          terrain: 'land',
          position: 0,
          trench: 2,
          target: 'defend',
          units: [{ unit: 'inf', count: 12, hpPct: 100 }],
        },
      ],
    },
  },
}

describe('buildDxcalcPayload', () => {
  it('matches the probe-recovered field grammar', () => {
    const p = buildDxcalcPayload(SETUP)
    expect(p['A.1.target']).toBe('B.1')
    expect(p['B.1.target']).toBe('0')
    expect(p['A.1.terrain']).toBe('land')
    expect(p['A.1.position']).toBe('0')
    expect(p['B.1.trench']).toBe('2')
    expect(p['A.1.1.unit']).toBe('inf')
    expect(p['A.1.1.count']).toBe('10')
    expect(p['A.1.1.hp']).toBe('100%')
    expect(p['A.1.2.unit']).toBe('art')
    expect(p['A.1.2.hp']).toBe('75%')
    expect(p['B.1.1.count']).toBe('12')
  })

  it('carries the globals and the onAttack marker', () => {
    const p = buildDxcalcPayload(SETUP)
    expect(p.MainSubmitButton).toBe('Start Battle')
    expect(p.maxRounds).toBe('10')
    expect(p.simulateVariance).toBe('')
    expect(p.updateCounts).toBe('')
    expect(p.newWindow).toBe('')
    expect(buildDxcalcPayload(SETUP, { variance: true }).simulateVariance).toBe('on')
  })

  it('sends blank building template rows', () => {
    const p = buildDxcalcPayload(SETUP)
    expect(p['A.1.bldg.0.abb']).toBe('')
    expect(p['A.1.bldg.0.lvl']).toBe('')
    expect(p['A.1.bldg.0.hp']).toBe('')
    expect(p['B.1.bldg.0.hp']).toBe('')
  })

  it('refuses the balloon-in-air batch killer', () => {
    const bad: BattleSetup = structuredClone(SETUP)
    bad.armies.A.stacks[0].terrain = 'air'
    bad.armies.A.stacks[0].units[0] = { unit: 'bal', count: 1, hpPct: 100 }
    expect(() => buildDxcalcPayload(bad)).toThrow(ExportGuardError)
  })
})
