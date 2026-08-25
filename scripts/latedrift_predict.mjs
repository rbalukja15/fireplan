/* PREDICT BEFORE SUBMITTING — the late-round output residual.

   From round seven of the real-army battle this engine deals 2.2%, then 5.6%,
   then 8.3% less damage than the site, on a state that matches the site's own
   readback exactly at the start of every one of those rounds. m(f) and E(n)
   are both measured to exhaustion, so the shortfall is somewhere else.

   Four prongs, and the first one is the cheap discriminator: the site's own
   round-6 and round-7 states, resubmitted as FRESH ONE-ROUND BATTLES. If a
   one-round answer from a state equals the increment the multi-round battle
   showed from that same state, the site is memoryless and the whole residual
   is reproducible in a single request. If it does not, the site carries
   something between rounds that no single-round measurement in this archive
   could ever have seen -- and this archive is 2,600 single rounds. */
import { writeFileSync } from 'node:fs';
import { simulate } from '../web/engine.js';

const HERE = new URL('..', import.meta.url).pathname;
const out = {};
const unitRows = (s) => s.rows.filter((r) => !r.isHero);
const heroOf = (s) => s.rows.find((r) => r.isHero);
const left = (r) => +(r.pool - r.hpLost).toFixed(3);
const alive = (r) => (r.unitsLeft ?? (r.count - r.deaths));

// --- G: the site's own mid-battle states, replayed as one round ------------
// Read straight off the readback in results.jsonl (experiment=fort_drift).
const STATES = {
  g6: { inf: [11, 120.4], ac: [6, 145.8], cav: [7, 110.9],
    def: [4, 150.5], hero: 58.7, fort: 42.2,
    // what the multi-round battle did NEXT, from this same state
    nextDef: 73.0, nextHero: 7.3, nextFort: 13.6 },
  g7: { inf: [10, 103.8], ac: [6, 127.7], cav: [6, 95.0],
    def: [3, 77.5], hero: 51.4, fort: 28.6,
    nextDef: 67.0, nextHero: 9.0, nextFort: 11.7 },
};
for (const [key, s] of Object.entries(STATES)) {
  const r = simulate({
    attacker: { rows: [
      { unit: 'inf', count: s.inf[0], hpPct: (s.inf[1] / (s.inf[0] * 20)) * 100 },
      { unit: 'ac', count: s.ac[0], hpPct: (s.ac[1] / (s.ac[0] * 60)) * 100 },
      { unit: 'cav', count: s.cav[0], hpPct: (s.cav[1] / (s.cav[0] * 25)) * 100 },
    ] },
    defender: {
      rows: [{ unit: 'ac', count: s.def[0], hpPct: (s.def[1] / (s.def[0] * 60)) * 100 }],
      hero: { code: 'kangal', level: 9, hpPct: (s.hero / 90) * 100 },
      buildings: [{ code: 'fortress', level: 1, hpPct: (s.fort / 50) * 100 }],
    },
    rounds: 1,
  });
  out[key] = {
    def_lost: +unitRows(r.defender)[0].hpLost.toFixed(3),
    hero_lost: +heroOf(r.defender).hpLost.toFixed(3),
    fort_lost: +r.defender.buildings[0].hpLost.toFixed(3),
    site_next: { def: s.nextDef, hero: s.nextHero, fort: s.nextFort },
  };
  console.log(`${key}: engine one round -> def ${out[key].def_lost}, hero ${out[key].hero_lost}, `
    + `fort ${out[key].fort_lost}   |   the multi-round battle did `
    + `def ${s.nextDef}, hero ${s.nextHero}, fort ${s.nextFort}`);
}

// --- H: the single-type deep ladder the gap asked for ----------------------
// 20 heavy tanks against 20, no fortress, no hero, no trench. One row a side
// means E(n) and m(f) are the ONLY two terms, and both are read back rather
// than inferred. Twelve rounds and neither side is wiped: both end on five
// units at f = 0.39, well down the curve.
console.log('\nH: 20 ht vs 20 ht, no fortress, no hero');
console.log('rd | A alive   A hp   A f    | B alive   B hp   B f');
for (let n = 1; n <= 12; n++) {
  const r = simulate({ attacker: { unit: 'ht', count: 20 },
    defender: { unit: 'ht', count: 20 }, rounds: n });
  const a = unitRows(r.attacker)[0]; const d = unitRows(r.defender)[0];
  const fr = (x) => +(left(x) / (Math.max(1, alive(x)) * 260)).toFixed(4);
  out[`h${n}`] = { a_alive: alive(a), a_hp: left(a), a_f: fr(a),
    b_alive: alive(d), b_hp: left(d), b_f: fr(d),
    a_lost: +r.attacker.hpLost.toFixed(3), b_lost: +r.defender.hpLost.toFixed(3),
    fought: r.rounds.fought };
  const o = out[`h${n}`];
  console.log(`${String(n).padStart(2)} | ${String(o.a_alive).padStart(7)} ${String(o.a_hp).padStart(7)} `
    + `${String(o.a_f).padStart(6)}  | ${String(o.b_alive).padStart(7)} ${String(o.b_hp).padStart(7)} ${String(o.b_f).padStart(6)}`);
}

// --- I and J: strip one thing at a time off the real army ------------------
// I removes the FORTRESS, J removes the HERO. Between them and H, every
// ingredient of the battle that shows the residual has been taken away once.
const RA = () => ({ rows: [
  { unit: 'inf', count: 35, hpPct: (453.6 / 700) * 100 },
  { unit: 'ac', count: 6, hpPct: (318.1 / 360) * 100 },
  { unit: 'cav', count: 17, hpPct: (378.1 / 425) * 100 },
] });
const RD = (fort, hero) => ({
  rows: [{ unit: 'ac', count: 12, hpPct: (677.5 / 720) * 100 }],
  ...(hero ? { hero: { code: 'kangal', level: 9, hpPct: (83.1 / 90) * 100 } } : {}),
  ...(fort ? { buildings: [{ code: 'fortress', level: 4, hpPct: 100 }] } : {}),
});
console.log('\nI: the real army with NO FORTRESS   J: with NO HERO');
// Round counts picked from the engine's own fought= figure, not from the
// real army's schedule: strip the fortress and the battle is over by round
// four, so asking for five, six and seven would have bought three copies of
// the same answer. Strip only the hero and it runs to seven.
for (const [tag, fort, hero, list] of [['i', false, true, [2, 3, 4]], ['j', true, false, [5, 6, 7]]]) {
  for (const n of list) {
    const r = simulate({ attacker: RA(), defender: RD(fort, hero), rounds: n });
    const d = unitRows(r.defender)[0];
    const h = heroOf(r.defender);
    out[`${tag}${n}`] = {
      inf: [alive(unitRows(r.attacker)[0]), left(unitRows(r.attacker)[0])],
      ac: [alive(unitRows(r.attacker)[1]), left(unitRows(r.attacker)[1])],
      cav: [alive(unitRows(r.attacker)[2]), left(unitRows(r.attacker)[2])],
      def: [alive(d), left(d)],
      hero_hp: h ? left(h) : null,
      fort_hp: fort ? +r.defender.buildings[0].hp.toFixed(3) : null,
      fought: r.rounds.fought, def_wiped: !!r.defender.wiped,
    };
    const o = out[`${tag}${n}`];
    console.log(`${tag}${n}: inf ${o.inf} ac ${o.ac} cav ${o.cav} | def ${o.def} `
      + `hero ${o.hero_hp} fort ${o.fort_hp} fought ${o.fought}`);
  }
}
writeFileSync(`${HERE}/latedrift_pred.json`, JSON.stringify(out, null, 1));
console.log('\npredictions written BEFORE any request was sent');
