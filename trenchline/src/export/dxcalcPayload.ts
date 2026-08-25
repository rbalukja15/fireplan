import type { BattleSetup, Side, Stack } from '../engine/types.ts'

/* Builds the exact form body dxcalc.com/s1914 expects, per the field grammar
 * recovered by dxcalc_probe.py and the captured last_response.html:
 *   per stack:  X.n.target  X.n.terrain  X.n.position  X.n.trench
 *   per row:    X.n.r.unit  X.n.r.count  X.n.r.hp        (rows index from 1)
 *   buildings:  X.n.bldg.0.abb/.lvl/.hp                  (blank = ignored)
 *   globals:    maxRounds  simulateVariance  updateCounts  newWindow
 *   marker:     MainSubmitButton = "Start Battle"  (injected client-side by
 *               onAttack(); without it the server re-renders the bare form)
 * Probe conventions honored: checkboxes are "on"/"" (the only tested
 * encoding), unused rows are sent blank rather than omitted, and the one
 * known batch-killer combination (balloon in air terrain) is refused. */

export const DXCALC_URL = 'https://dxcalc.com/s1914'

export class ExportGuardError extends Error {}

export function buildDxcalcPayload(
  setup: BattleSetup,
  options: { variance?: boolean } = {},
): Record<string, string> {
  guardPayload(setup)
  const payload: Record<string, string> = {
    maxRounds: String(setup.maxRounds),
    simulateVariance: options.variance ? 'on' : '',
    updateCounts: '',
    newWindow: '',
    MainSubmitButton: 'Start Battle',
  }
  for (const side of ['A', 'B'] as const) {
    setup.armies[side].stacks.forEach((stack, i) => {
      addStack(payload, side, i + 1, stack)
    })
  }
  return payload
}

function addStack(
  payload: Record<string, string>,
  side: Side,
  n: number,
  stack: Stack,
): void {
  const other = side === 'A' ? 'B' : 'A'
  const prefix = `${side}.${n}`
  payload[`${prefix}.target`] =
    stack.target === 'defend' ? '0' : `${other}.${stack.target + 1}`
  payload[`${prefix}.terrain`] = stack.terrain
  payload[`${prefix}.position`] = String(stack.position)
  payload[`${prefix}.trench`] = String(stack.trench)
  stack.units.forEach((row, r) => {
    payload[`${prefix}.${r + 1}.unit`] = row.unit
    payload[`${prefix}.${r + 1}.count`] = row.count > 0 ? String(row.count) : ''
    payload[`${prefix}.${r + 1}.hp`] = row.count > 0 ? `${row.hpPct}%` : ''
  })
  // blank building template row — rows without HP are ignored server-side
  payload[`${prefix}.bldg.0.abb`] = ''
  payload[`${prefix}.bldg.0.lvl`] = ''
  payload[`${prefix}.bldg.0.hp`] = ''
}

/** Port of the probe's guard_payload(): a Balloon in 'air' terrain makes the
 * server silently return the bare form and aborts the whole batch. */
export function guardPayload(setup: BattleSetup): void {
  for (const side of ['A', 'B'] as const) {
    for (const stack of setup.armies[side].stacks) {
      if (stack.terrain !== 'air') continue
      if (stack.units.some((u) => u.unit === 'bal' && u.count > 0)) {
        throw new ExportGuardError(
          'dxCalc silently rejects a Balloon in air terrain and aborts the whole ' +
            'battle — move the balloon or change the terrain before exporting.',
        )
      }
    }
  }
}
