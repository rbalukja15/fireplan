import type { BattleConfig, SideConfig } from '../engine/research.ts'
import { FIGHT_OUT_ROUNDS, UNITS } from '../engine/research.ts'

/* Builds the exact form body dxcalc.com/s1914 expects, per the field grammar
 * recovered by dxcalc_probe.py and the captured last_response.html:
 *   per stack:  X.n.target  X.n.terrain  X.n.position  X.n.trench
 *   per row:    X.n.r.unit  X.n.r.count  X.n.r.hp        (rows index from 1)
 *   hero:       X.n.hero.abb/.lvl/.hp                    (injected by addHero)
 *   buildings:  X.n.bldg.k.abb/.lvl/.hp                  (k indexes from 0)
 *   globals:    maxRounds  simulateVariance  updateCounts  newWindow
 *   marker:     MainSubmitButton = "Start Battle"  (injected client-side by
 *               onAttack(); without it the server re-renders the bare form)
 * Probe conventions honored: checkboxes are "on"/"" (the only tested
 * encoding), unused rows are sent blank rather than omitted, and the one
 * known batch-killer combination (balloon in air terrain) is refused. */

export const DXCALC_URL = 'https://dxcalc.com/s1914'

export class ExportGuardError extends Error {}

/** dxcalc wants one terrain per stack; the engine model keeps air-ness in the
 * unit class. An all-air side exports as 'air' (or 'patrol' for the attacker
 * in patrol mode); otherwise the configured terrain is used. */
function stackTerrain(side: SideConfig, configured: string, patrol: boolean): string {
  const rows = side.rows.filter((r) => r.count > 0)
  const allAir = rows.length > 0 && rows.every((r) => UNITS[r.unit]?.cls === 'air')
  if (allAir) return patrol ? 'patrol' : 'air'
  return configured
}

export function buildDxcalcPayload(
  cfg: BattleConfig,
  options: { variance?: boolean } = {},
): Record<string, string> {
  const atkTerrain = stackTerrain(cfg.attacker, cfg.terrain, cfg.mode === 'patrol')
  const defTerrain = stackTerrain(
    cfg.defender,
    cfg.defenderTerrain || cfg.terrain,
    false,
  )
  guardPayload(cfg.attacker, atkTerrain)
  guardPayload(cfg.defender, defTerrain)

  const payload: Record<string, string> = {
    maxRounds: String(cfg.fightToEnd ? FIGHT_OUT_ROUNDS : cfg.rounds),
    simulateVariance: options.variance ? 'on' : '',
    updateCounts: '',
    newWindow: '',
    MainSubmitButton: 'Start Battle',
  }
  addStack(payload, 'A', cfg.attacker, {
    target: 'B.1',
    terrain: atkTerrain,
    position: 0,
  })
  addStack(payload, 'B', cfg.defender, {
    target: cfg.mutual ? 'A.1' : '0',
    terrain: defTerrain,
    position: cfg.distance,
  })
  return payload
}

function addStack(
  payload: Record<string, string>,
  side: 'A' | 'B',
  s: SideConfig,
  meta: { target: string; terrain: string; position: number },
): void {
  const prefix = `${side}.1`
  payload[`${prefix}.target`] = meta.target
  payload[`${prefix}.terrain`] = meta.terrain
  payload[`${prefix}.position`] = String(meta.position)
  payload[`${prefix}.trench`] = String(s.trench)

  s.rows.forEach((row, r) => {
    payload[`${prefix}.${r + 1}.unit`] = row.unit
    payload[`${prefix}.${r + 1}.count`] = row.count > 0 ? String(row.count) : ''
    payload[`${prefix}.${r + 1}.hp`] = row.count > 0 ? `${row.hpPct}%` : ''
  })

  if (s.hero) {
    payload[`${prefix}.hero.abb`] = s.hero.code
    payload[`${prefix}.hero.lvl`] = String(s.hero.level)
    payload[`${prefix}.hero.hp`] = `${s.hero.hpPct}%`
  }

  // bldg rows index from 0; a trailing blank row mirrors the stock form's
  // template row (rows without HP are ignored server-side).
  s.buildings.forEach((b, k) => {
    payload[`${prefix}.bldg.${k}.abb`] = b.code
    payload[`${prefix}.bldg.${k}.lvl`] = String(b.level)
    payload[`${prefix}.bldg.${k}.hp`] = `${b.hpPct}%`
  })
  const blank = s.buildings.length
  payload[`${prefix}.bldg.${blank}.abb`] = ''
  payload[`${prefix}.bldg.${blank}.lvl`] = ''
  payload[`${prefix}.bldg.${blank}.hp`] = ''
}

/** Port of the probe's guard_payload(): a Balloon in 'air' terrain makes the
 * server silently return the bare form and aborts the whole batch. */
export function guardPayload(side: SideConfig, terrain: string): void {
  if (terrain !== 'air' && terrain !== 'patrol') return
  if (side.rows.some((r) => r.unit === 'bal' && r.count > 0)) {
    throw new ExportGuardError(
      'dxCalc silently rejects a Balloon in air terrain and aborts the whole ' +
        'battle — remove the balloon before exporting (measure balloons in land terrain).',
    )
  }
}
