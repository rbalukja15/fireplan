import type { BattleReport, BattleSetup, EngineData, Side } from './types.ts'
import { mulberry32 } from './formulas.ts'
import { simulate } from './simulate.ts'

export interface Distribution {
  min: number
  mean: number
  max: number
}

export interface MonteCarloResult {
  runs: number
  winProbability: Record<Side | 'draw' | 'stalemate', number>
  rounds: Distribution
  hpLost: Record<Side, Distribution>
  /** One representative full report (the median-rounds run) for display. */
  sample: BattleReport
}

function dist(values: number[]): Distribution {
  const min = Math.min(...values)
  const max = Math.max(...values)
  const mean = values.reduce((a, b) => a + b, 0) / values.length
  return { min, mean, max }
}

/** Repeats the battle with the ±variance roll active. Seeded, so the same
 * setup always yields the same probabilities. The roll's true distribution
 * has never been sampled by the probe — treat the spread as indicative. */
export function monteCarlo(
  setup: BattleSetup,
  data: EngineData,
  runs = 200,
  seed = 1234,
): MonteCarloResult {
  const rng = mulberry32(seed)
  const reports: BattleReport[] = []
  for (let i = 0; i < runs; i++) {
    reports.push(simulate(setup, data, rng))
  }
  const wins: MonteCarloResult['winProbability'] = { A: 0, B: 0, draw: 0, stalemate: 0 }
  for (const r of reports) wins[r.winner] += 1 / runs

  const byRounds = [...reports].sort((a, b) => a.rounds - b.rounds)
  const sample = byRounds[Math.floor(byRounds.length / 2)]

  return {
    runs,
    winProbability: wins,
    rounds: dist(reports.map((r) => r.rounds)),
    hpLost: {
      A: dist(reports.map((r) => r.sides.A.hpLost)),
      B: dist(reports.map((r) => r.sides.B.hpLost)),
    },
    sample,
  }
}
