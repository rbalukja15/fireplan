/* PREDICT BEFORE SUBMITTING — the real army, round by round, at a FULL level-4
   fortress.

   The archive already has this ladder at a fortress of 155 (level 4 at 5/50),
   where the engine reproduces every round exactly. The one configuration that
   does not reproduce is the same army against a fortress of 200, and the whole
   difference between them is which side of the race the building lands on.

   These are the per-round SURVIVOR COUNTS and REMAINING HP the engine expects,
   written down before the site is asked, so the round the two first part
   company can be pointed at instead of argued about. */
import { readFileSync, writeFileSync } from 'node:fs';
import { simulate } from '../web/engine.js';

const HERE = new URL('..', import.meta.url).pathname;
const ATK = () => ({ rows: [
  { unit: 'inf', count: 35, hpPct: (453.6 / 700) * 100 },
  { unit: 'ac', count: 6, hpPct: (318.1 / 360) * 100 },
  { unit: 'cav', count: 17, hpPct: (378.1 / 425) * 100 },
] });
const DEF = (fortPct, hero) => ({
  rows: [{ unit: 'ac', count: 12, hpPct: (677.5 / 720) * 100 }],
  ...(hero ? { hero: { code: 'kangal', level: 9, hpPct: (83.1 / 90) * 100 } } : {}),
  buildings: [{ code: 'fortress', level: 4, hpPct: fortPct }],
});

const out = {};
// A side's `rows` INCLUDES its hero row, and the hero comes first. Reading
// rows[0] as "the unit row" gave a defender of 1 unit in every round, which
// looked like a catastrophic round-one wipe and was nothing but the wrong
// index. Pick by isHero, and prefer the engine's own unitsLeft over
// count - deaths.
const row = (r) => ({
  alive: r.unitsLeft !== null && r.unitsLeft !== undefined ? r.unitsLeft : r.count - r.deaths,
  hpLeft: +(r.pool - r.hpLost).toFixed(2),
});
const units = (side) => side.rows.filter((r) => !r.isHero);
const heroRow = (side) => side.rows.find((r) => r.isHero);

console.log('rd | inf ct   hp | ac ct   hp | cav ct   hp | def ct    hp | hero  | fort hp | fought wiped');
for (let n = 1; n <= 9; n++) {
  const r = simulate({ attacker: ATK(), defender: DEF(100, true), rounds: n });
  const [a1, a2, a3] = units(r.attacker).map(row);
  const d1 = row(units(r.defender)[0]);
  const h = heroRow(r.defender);
  const b = r.defender.buildings[0];
  out[`r${n}`] = {
    inf: a1, ac: a2, cav: a3, def: d1,
    hero_hp: h ? +(h.pool - h.hpLost).toFixed(2) : null,
    fort_hp: +b.hp.toFixed(2), fort_lost: +b.hpLost.toFixed(2), fort_destroyed: b.destroyed,
    atk_lost: +r.attacker.hpLost.toFixed(2), def_lost: +r.defender.hpLost.toFixed(2),
    fought: r.rounds.fought, def_wiped: !!r.defender.wiped,
  };
  const o = out[`r${n}`];
  console.log(`${String(n).padStart(2)} | ${String(a1.alive).padStart(6)} ${String(a1.hpLeft).padStart(6)}`
    + ` | ${String(a2.alive).padStart(5)} ${String(a2.hpLeft).padStart(6)}`
    + ` | ${String(a3.alive).padStart(6)} ${String(a3.hpLeft).padStart(6)}`
    + ` | ${String(d1.alive).padStart(6)} ${String(d1.hpLeft).padStart(7)}`
    + ` | ${String(o.hero_hp).padStart(6)} | ${String(o.fort_hp).padStart(7)} | ${o.fought} ${o.def_wiped}`);
}
// The two endgame controls, at 100 rounds.
out.no_hero_100 = (() => {
  const r = simulate({ attacker: ATK(), defender: DEF(100, false), rounds: 100 });
  const b = r.defender.buildings[0];
  return { fort_lost: +b.hpLost.toFixed(2), fort_destroyed: b.destroyed,
    fought: r.rounds.fought, def_lost: +r.defender.hpLost.toFixed(2) };
})();
out.prongA_with_hero_100 = (() => {
  const r = simulate({
    attacker: { unit: 'ht', count: 6 },
    defender: { unit: 'inf', count: 5,
      hero: { code: 'kangal', level: 9 },
      buildings: [{ code: 'fortress', level: 5 }] },
    rounds: 100,
  });
  const b = r.defender.buildings[0];
  return { fort_lost: +b.hpLost.toFixed(2), fort_destroyed: b.destroyed,
    fought: r.rounds.fought, def_lost: +r.defender.hpLost.toFixed(2) };
})();
console.log('\nno hero, 100 rounds :', JSON.stringify(out.no_hero_100));
console.log('prong A + a hero    :', JSON.stringify(out.prongA_with_hero_100));
writeFileSync(`${HERE}/fortdrift_pred.json`, JSON.stringify(out, null, 1));
console.log('\npredictions written BEFORE any request was sent');
