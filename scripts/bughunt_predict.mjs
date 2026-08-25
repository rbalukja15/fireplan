/* PREDICT BEFORE SUBMITTING.

   Run this, then `python3 dxcalc_probe.py --run bughunt`. The predictions go
   to disk and are copied into the meta of every results.jsonl row beside the
   reading they were made against, so a prediction cannot be quietly adjusted
   once the site has answered -- which is the only thing that makes a
   predict-first sweep worth more than a fit.

   bughunt_cells.json is committed; bughunt_pred.json is NOT, because it is
   derived from web/engine.js and goes stale the moment the engine changes.
   exp_bughunt refuses to submit against a prediction file older than the
   engine that produced it. */
import { readFileSync, writeFileSync } from 'node:fs';
import { simulate } from '../web/engine.js';

const S = process.env.BUGHUNT_DIR || new URL('..', import.meta.url).pathname;
const cells = JSON.parse(readFileSync(`${S}/bughunt_cells.json`, 'utf8'));
const out = {};

for (const c of cells) {
  const cfg = {
    attacker: { unit: c.atk.unit, count: c.atk.count, trench: c.atkTrench || 0 },
    defender: {
      unit: c.def.unit, count: c.def.count, trench: c.defTrench || 0,
      buildings: c.fortress ? [{ code: 'fortress', level: c.fortress }] : [],
    },
    rounds: c.rounds,
  };
  const r = simulate(cfg);
  const b = (r.defender.buildings || [])[0];
  out[c.id] = {
    atk_lost: +r.attacker.hpLost.toFixed(2),
    def_lost: +r.defender.hpLost.toFixed(2),
    bldg_lost: b ? +b.hpLost.toFixed(2) : null,
    atk_dead: r.attacker.deaths ?? null,
    def_dead: r.defender.deaths ?? null,
    def_wiped: !!r.defender.wiped,
    rounds_fought: r.rounds ? r.rounds.fought : null,
    coverage: r.coverage.level,
  };
  const p = out[c.id];
  console.log(`${c.id.padEnd(3)} ${c.prong.padEnd(26)} r=${String(c.rounds).padEnd(3)} `
    + `A=${String(p.atk_lost).padStart(9)}  B=${String(p.def_lost).padStart(9)}  `
    + `bldg=${String(p.bldg_lost).padStart(7)}  Bdead=${p.def_dead}  wiped=${p.def_wiped}  `
    + `fought=${p.rounds_fought}`);
}
writeFileSync(`${S}/bughunt_pred.json`, JSON.stringify(out, null, 1));
console.log('\npredictions written BEFORE any request was sent');
