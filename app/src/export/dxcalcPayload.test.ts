import { describe, expect, it } from 'vitest'
import type { BattleConfig, SideConfig } from '../engine/research.ts'
import { ExportGuardError, buildDxcalcPayload } from './dxcalcPayload.ts'

function base(): BattleConfig {
  const attacker: SideConfig = {
    rows: [
      { unit: 'inf', count: 10, hpPct: 100 },
      { unit: 'art', count: 2, hpPct: 75 },
    ],
    trench: 0,
    buildings: [],
    hero: { code: 'hank', level: 12, hpPct: 90 },
  }
  const defender: SideConfig = {
    rows: [{ unit: 'inf', count: 12, hpPct: 100 }],
    trench: 2,
    buildings: [{ code: 'fortress', level: 3, hpPct: 80 }],
    hero: null,
  }
  return {
    attacker,
    defender,
    rounds: 10,
    fightToEnd: false,
    mode: 'strike',
    terrain: 'land',
    defenderTerrain: '',
    distance: 0,
    mutual: false,
  }
}

describe('buildDxcalcPayload', () => {
  it('matches the probe-recovered field grammar', () => {
    const p = buildDxcalcPayload(base())
    expect(p['A.1.target']).toBe('B.1')
    expect(p['B.1.target']).toBe('0')
    expect(p['A.1.terrain']).toBe('land')
    expect(p['B.1.trench']).toBe('2')
    expect(p['A.1.1.unit']).toBe('inf')
    expect(p['A.1.2.hp']).toBe('75%')
    expect(p['B.1.1.count']).toBe('12')
    expect(p.MainSubmitButton).toBe('Start Battle')
    expect(p.maxRounds).toBe('10')
    expect(p.simulateVariance).toBe('')
  })

  it('exports hero rows via the addHero() field names', () => {
    const p = buildDxcalcPayload(base())
    expect(p['A.1.hero.abb']).toBe('hank')
    expect(p['A.1.hero.lvl']).toBe('12')
    expect(p['A.1.hero.hp']).toBe('90%')
    expect(p['B.1.hero.abb']).toBeUndefined()
  })

  it('exports building rows indexed from 0, with a trailing blank template row', () => {
    const p = buildDxcalcPayload(base())
    expect(p['B.1.bldg.0.abb']).toBe('fortress')
    expect(p['B.1.bldg.0.lvl']).toBe('3')
    expect(p['B.1.bldg.0.hp']).toBe('80%')
    expect(p['B.1.bldg.1.abb']).toBe('')
    expect(p['A.1.bldg.0.abb']).toBe('')
  })

  it('fight-to-the-finish exports the source calculator cap', () => {
    const p = buildDxcalcPayload({ ...base(), fightToEnd: true })
    expect(p.maxRounds).toBe('100')
  })

  it('mutual sets the defender attacking back', () => {
    const p = buildDxcalcPayload({ ...base(), mutual: true })
    expect(p['B.1.target']).toBe('A.1')
  })

  it('distance becomes the defender position', () => {
    const p = buildDxcalcPayload({ ...base(), distance: 30 })
    expect(p['A.1.position']).toBe('0')
    expect(p['B.1.position']).toBe('30')
  })

  it('an all-air attacker exports air terrain, patrol mode exports patrol', () => {
    const cfg = base()
    cfg.attacker.rows = [{ unit: 'tac', count: 3, hpPct: 100 }]
    cfg.attacker.hero = null
    expect(buildDxcalcPayload(cfg)['A.1.terrain']).toBe('air')
    expect(buildDxcalcPayload({ ...cfg, mode: 'patrol' })['A.1.terrain']).toBe('patrol')
  })

  it('refuses the balloon-in-air batch killer', () => {
    const cfg = base()
    cfg.attacker.rows = [{ unit: 'bal', count: 1, hpPct: 100 }]
    cfg.attacker.hero = null
    expect(() => buildDxcalcPayload(cfg)).toThrow(ExportGuardError)
  })
})
