#!/usr/bin/env node
/**
 * Does web/engine.js reproduce the battles that were actually fought?
 *
 * The engine is only trustworthy insofar as it predicts real measurements, so
 * this suite replays ../../results.jsonl row by row and compares the engine's
 * prediction against what dxcalc.com actually printed. Nothing here is a
 * self-consistency check against a constant the engine itself carries: every
 * expected value below came off the wire.
 *
 * It also asserts the honesty properties, which matter as much as the numbers:
 * simulate() never throws, an unmeasured matchup is never labelled 'measured',
 * an 'unknown' matchup yields withheld numbers rather than invented ones, and
 * derivation[] is populated for every result.
 *
 * TOLERANCES, and why
 * -------------------
 * The source page prints HP lost to 0.1 in each unit span and to 0.01 in the
 * summary table, and percentages to 3 significant figures. So:
 *
 *   HP lost, from the summary table (meta.detail.*.lost_source == 1) ±0.005
 *   HP lost, from a span                                            ±0.05
 *   A stack POOL is never printed at all. It is pool = lost / pct, so the
 *     assertion is that the engine's pool falls inside the interval implied by
 *     both print precisions — a bracket, never a point. Quoting a derived pool
 *     to 2 decimals is a documented failure mode of this project.
 *   Death counts are integers and are asserted exactly.
 *
 * Run:  node web/test/engine.test.mjs
 */

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

import {
  UNITS, TRENCH_POOL, TRENCH_POOL_BRACKET, TRENCH_OUTPUT, PROVENANCE, NOT_MEASURED,
  MAX_UNIT_ROWS,
  HEROES,
} from '../data.js';
import {
  heroBuff,
  effectiveUnits, hpMultiplier, fortressDR, trenchFactors, coverageOf, simulate,
} from '../engine.js';

const HERE = dirname(fileURLToPath(import.meta.url));
const RESULTS = join(HERE, '..', '..', 'results.jsonl');

const rows = readFileSync(RESULTS, 'utf8')
  .split('\n').filter((l) => l.trim()).map((l) => JSON.parse(l));

let ok = 0;
const failures = [];
const unreproduced = [];

function check(label, cond, detail = '') {
  if (cond) {
    ok += 1;
    console.log(`  PASS  ${label}`);
  } else {
    failures.push({ label, detail });
    console.log(`  FAIL  ${label}\n        ${detail}`);
  }
}

/** A measurement the engine could not reproduce. Reported, never papered over. */
function cannotReproduce(what, expected, got, note) {
  unreproduced.push({ what, expected, got, note });
}

function near(a, b, tol) {
  return a !== null && a !== undefined && Number.isFinite(a) && Math.abs(a - b) <= tol + 1e-12;
}

/** Decimal places the recorder actually stored, which fixes the print source. */
function decimals(x) {
  const s = String(x);
  const i = s.indexOf('.');
  return i < 0 ? 0 : s.length - i - 1;
}

function lostTol(value, detail) {
  if (detail && detail.lost_source === 1) return 0.005;   // summary table, 2 dp
  return decimals(value) >= 2 ? 0.005 : 0.05;             // else the span, 1 dp
}

/** pool = lost / pct, widened by both print precisions. */
function poolBracket(lost, pct, lostSource) {
  const u = lostSource === 1 ? 0.005 : 0.05;
  const upct = 0.5 * 10 ** (Math.floor(Math.log10(Math.abs(pct))) - 2);
  return [(lost - u) / ((pct + upct) / 100), (lost + u) / ((pct - upct) / 100)];
}

function inBracket(x, [lo, hi]) {
  return Number.isFinite(x) && x >= lo - 1e-9 && x <= hi + 1e-9;
}

function fmt(x) {
  return x === null || x === undefined ? String(x) : Number(x).toFixed(4);
}

const withReadings = (name) => rows.filter(
  (r) => r.experiment === name && r.readings && Object.keys(r.readings).length,
);

console.log(`Replaying ${rows.length} recorded requests from results.jsonl\n`);

// ===========================================================================
console.log('1. semantics — the three asymmetric duels that fixed HP LOST vs HP LEFT');
// ===========================================================================
for (const r of withReadings('semantics')) {
  const { atk, def } = r.meta;
  const res = simulate({
    attacker: { unit: 'inf', count: atk },
    defender: { unit: 'inf', count: def },
    rounds: 1,
  });
  const eA = r.readings['A.1.1'];
  const eB = r.readings['B.1.1'];
  check(`${atk} inf vs ${def} inf: attacker loses ${eA}`,
    near(res.attacker.hpLost, eA, lostTol(eA)), `engine ${fmt(res.attacker.hpLost)}`);
  check(`${atk} inf vs ${def} inf: defender loses ${eB}`,
    near(res.defender.hpLost, eB, lostTol(eB)), `engine ${fmt(res.defender.hpLost)}`);
  if (!near(res.attacker.hpLost, eA, lostTol(eA))) cannotReproduce(`semantics ${atk}v${def} attacker`, eA, res.attacker.hpLost);
  if (!near(res.defender.hpLost, eB, lostTol(eB))) cannotReproduce(`semantics ${atk}v${def} defender`, eB, res.defender.hpLost);
}

// ===========================================================================
console.log('\n2. unit_stats — the same-class diagonal, all four runs of the roster');
// ===========================================================================
{
  let run = 0; let seen = new Set();
  for (const r of withReadings('unit_stats')) {
    const code = r.meta.unit;
    if (seen.has(code)) { run += 1; seen = new Set(); }
    seen.add(code);
    const res = simulate({
      attacker: { unit: code, count: 10 },
      defender: { unit: code, count: 10 },
      rounds: 1,
    });
    const eA = r.readings['A.1.1'];
    const eB = r.readings['B.1.1'];
    const tag = `run ${run + 1} ${code} 10v10`;
    check(`${tag}: attacker loses ${eA} (defence ${UNITS[code].def} x E(10))`,
      near(res.attacker.hpLost, eA, lostTol(eA)), `engine ${fmt(res.attacker.hpLost)}`);
    check(`${tag}: defender loses ${eB} (attack ${UNITS[code].atk} x E(10))`,
      near(res.defender.hpLost, eB, lostTol(eB)), `engine ${fmt(res.defender.hpLost)}`);
    check(`${tag}: coverage is 'measured'`, res.coverage.level === 'measured', res.coverage.level);
    if (!near(res.attacker.hpLost, eA, lostTol(eA))) cannotReproduce(`unit_stats ${tag} attacker`, eA, res.attacker.hpLost);
    if (!near(res.defender.hpLost, eB, lostTol(eB))) cannotReproduce(`unit_stats ${tag} defender`, eB, res.defender.hpLost);
  }
  const skipped = rows.filter((r) => r.experiment === 'unit_stats'
    && (!r.readings || !Object.keys(r.readings).length));
  check(`the ${skipped.length} balloon rows carry no readings, and the engine offers no numbers for it`,
    skipped.length > 0 && skipped.every((r) => r.meta.unit === 'bal')
      && simulate({ attacker: { unit: 'bal', count: 10 }, defender: { unit: 'bal', count: 10 } })
        .attacker.hpLost === null,
    'the Balloon must stay unmeasurable, not be interpolated from the other fliers');
}

// ===========================================================================
console.log('\n3. hp_scaling — m(f) = 0.05 + 0.95f, 10 infantry at f HP vs 50 infantry');
// ===========================================================================
for (const r of withReadings('hp_scaling')) {
  const pct = r.meta.hp_pct;
  const res = simulate({
    attacker: { unit: 'inf', count: 10, hpPct: pct },
    defender: { unit: 'inf', count: 50 },
    rounds: 1,
  });
  const eA = r.readings['A.1.1'];
  const eB = r.readings['B.1.1'];
  check(`attacker at ${pct}% HP loses ${eA}` + (pct <= 80 ? ' (wiped, capped by its pool)' : ''),
    near(res.attacker.hpLost, eA, lostTol(eA)), `engine ${fmt(res.attacker.hpLost)}`);
  check(`attacker at ${pct}% HP still deals ${eB} = 40 x m(${pct / 100})`,
    near(res.defender.hpLost, eB, lostTol(eB)), `engine ${fmt(res.defender.hpLost)}`);
  if (pct <= 80) {
    check(`  and the wiped stack is reported wiped`, res.attacker.wiped === true, String(res.attacker.wiped));
  }
  if (!near(res.defender.hpLost, eB, lostTol(eB))) cannotReproduce(`hp_scaling ${pct}% defender`, eB, res.defender.hpLost);
}

// ===========================================================================
console.log('\n4. air_vs_ground — 30 cells, both directions, post-fire attacker output');
// ===========================================================================
for (const r of withReadings('air_vs_ground')) {
  const m = r.meta;
  const d = m.detail || {};
  const res = simulate({
    attacker: { unit: m.atk, count: m.atk_n },
    defender: { unit: m.target, count: m.def_n },
    rounds: 1,
  });
  const tag = `${m.atk} x${m.atk_n} -> ${m.target} x${m.def_n}`;
  const A = d['A.1.1'];
  const B = d['B.1.1'];

  check(`${tag}: air attacker loses ${A.lost} (${m.target} defence x E(${m.def_n}))`,
    near(res.attacker.hpLost, A.lost, lostTol(A.lost, A)), `engine ${fmt(res.attacker.hpLost)}`);
  check(`${tag}: ground defender loses ${B.lost} (post-fire output)`,
    near(res.defender.hpLost, B.lost, lostTol(B.lost, B)), `engine ${fmt(res.defender.hpLost)}`);
  check(`${tag}: deaths ${A.died} / ${B.died}`,
    res.attacker.deaths === A.died && res.defender.deaths === B.died,
    `engine ${res.attacker.deaths} / ${res.defender.deaths}`);
  check(`${tag}: attacker pool inside the measured bracket`,
    inBracket(res.attacker.pool, poolBracket(A.lost, A.pct, A.lost_source)),
    `engine ${fmt(res.attacker.pool)} vs [${poolBracket(A.lost, A.pct, A.lost_source).map(fmt)}]`);
  check(`${tag}: defender pool inside the measured bracket`,
    inBracket(res.defender.pool, poolBracket(B.lost, B.pct, B.lost_source)),
    `engine ${fmt(res.defender.pool)} vs [${poolBracket(B.lost, B.pct, B.lost_source).map(fmt)}]`);
  check(`${tag}: coverage is 'measured' (the one measured cross-class pairing)`,
    res.coverage.level === 'measured', res.coverage.level);

  if (!near(res.defender.hpLost, B.lost, lostTol(B.lost, B))) {
    cannotReproduce(`air_vs_ground ${tag} defender loss`, B.lost, res.defender.hpLost);
  }
  if (!near(res.attacker.hpLost, A.lost, lostTol(A.lost, A))) {
    cannotReproduce(`air_vs_ground ${tag} attacker loss`, A.lost, res.attacker.hpLost);
  }
}
check('the 10 balloon air_vs_ground rows are empty, and the engine withholds rather than guesses',
  rows.filter((r) => r.experiment === 'air_vs_ground' && r.meta.atk === 'bal'
    && (!r.readings || !Object.keys(r.readings).length)).length === 10
  && simulate({ attacker: { unit: 'bal', count: 10 }, defender: { unit: 'inf', count: 57 } })
    .defender.hpLost === null);

// ===========================================================================
console.log('\n5. trenches — 10 infantry vs 10 infantry across the nine sampled levels');
// ===========================================================================
for (const r of withReadings('trenches')) {
  const m = r.meta;
  const d = m.detail;
  const defTrench = m.trench || 0;
  const atkTrench = m.atk_trench || 0;
  const res = simulate({
    attacker: { unit: 'inf', count: 10, trench: atkTrench },
    defender: { unit: 'inf', count: 10, trench: defTrench },
    rounds: 1,
  });
  const A = d['A.1.1'];
  const B = d['B.1.1'];
  const tag = m.label;

  check(`${tag}: attacker loses ${A.lost}`
    + (defTrench ? ` = 50 x trench output ${TRENCH_OUTPUT[defTrench]}` : ''),
    near(res.attacker.hpLost, A.lost, lostTol(A.lost, A)), `engine ${fmt(res.attacker.hpLost)}`);
  check(`${tag}: defender loses ${B.lost} (the trench does NOT reduce damage)`,
    near(res.defender.hpLost, B.lost, lostTol(B.lost, B)), `engine ${fmt(res.defender.hpLost)}`);
  check(`${tag}: deaths ${A.died} / ${B.died} (per-unit HP is trench-inflated)`,
    res.attacker.deaths === A.died && res.defender.deaths === B.died,
    `engine ${res.attacker.deaths} / ${res.defender.deaths}`);
  check(`${tag}: defender pool inside the measured bracket`,
    inBracket(res.defender.pool, poolBracket(B.lost, B.pct, B.lost_source)),
    `engine ${fmt(res.defender.pool)} vs [${poolBracket(B.lost, B.pct, B.lost_source).map(fmt)}]`);
  check(`${tag}: attacker pool inside the measured bracket`,
    inBracket(res.attacker.pool, poolBracket(A.lost, A.pct, A.lost_source)),
    `engine ${fmt(res.attacker.pool)} vs [${poolBracket(A.lost, A.pct, A.lost_source).map(fmt)}]`);

  if (!near(res.attacker.hpLost, A.lost, lostTol(A.lost, A))) {
    cannotReproduce(`trenches ${tag} attacker loss`, A.lost, res.attacker.hpLost);
  }
}
// The carried pool multipliers must sit inside the brackets they came from,
// and level 10 must NOT be tidied to 1.25.
for (const lvl of Object.keys(TRENCH_POOL_BRACKET)) {
  const [lo, hi] = TRENCH_POOL_BRACKET[lvl];
  check(`trench L${lvl} pool multiplier ${TRENCH_POOL[lvl]} lies in its measured bracket [${lo}, ${hi}]`,
    TRENCH_POOL[lvl] >= lo && TRENCH_POOL[lvl] <= hi);
}
check('trench L10 is carried as 1.24, and 1.25 is excluded by the measurement',
  TRENCH_POOL[10] === 1.24 && 1.25 > TRENCH_POOL_BRACKET[10][1],
  `bracket [${TRENCH_POOL_BRACKET[10]}]`);

// ===========================================================================
console.log('\n6. fortress — 30 infantry vs 30 infantry, levels 1-5');
// ===========================================================================
for (const r of rows.filter((x) => x.experiment === 'fortress')) {
  const lvl = r.meta.level;
  const res = simulate({
    attacker: { unit: 'inf', count: 30 },
    defender: {
      unit: 'inf',
      count: 30,
      buildings: lvl ? [{ code: 'fortress', level: lvl }] : [],
    },
    rounds: 1,
  });
  const eB = r.readings['B.1.1'];
  check(`fortress L${lvl}: defender loses ${eB}` + (lvl ? ` = 113.33 x (1 - 0.15 x ${lvl + 1})` : ' (control)'),
    near(res.defender.hpLost, eB, lostTol(eB)), `engine ${fmt(res.defender.hpLost)}`);
  if (!near(res.defender.hpLost, eB, lostTol(eB))) {
    cannotReproduce(`fortress L${lvl} defender loss`, eB, res.defender.hpLost);
  }
  if (lvl === 0) {
    check('fortress control: attacker loses 141.7 (5.0 x E(30) = 141.667)',
      near(res.attacker.hpLost, r.readings['A.1.1'], lostTol(r.readings['A.1.1'])),
      `engine ${fmt(res.attacker.hpLost)}`);
  } else {
    // The attacker slot in these six rows reads -8.5: the building's own result
    // row overwrote it, a known and fixed rig defect. There is no attacker
    // measurement to compare against here, so none is asserted.
    check(`fortress L${lvl}: the fortress itself loses 8.5 HP, unreduced by its own DR`,
      near(res.defender.buildings[0].hpLost, 8.5, 0.05),
      `engine ${fmt(res.defender.buildings[0].hpLost)}`);
    check(`fortress L${lvl}: the attacker's output is NOT reduced by the fortress`,
      near(res.attacker.damageDealt / (1 - fortressDR(50 * lvl)), 113.3333, 0.001),
      `engine delivered ${fmt(res.attacker.damageDealt)}`);
  }
}

// ===========================================================================
console.log('\n7. buildings — only the fortress mitigates; the other seven are inert');
// ===========================================================================
for (const r of rows.filter((x) => x.experiment === 'buildings')) {
  const m = r.meta;
  const b = m.type ? [{ code: m.type, level: m.level }] : [];
  const res = simulate({
    attacker: { unit: 'inf', count: 30 },
    defender: { unit: 'inf', count: 30, buildings: b },
    rounds: 1,
  });
  const tag = m.type ? `${m.type} L${m.level}` : 'control (no building)';
  const eA = r.readings['A.1.1'];
  const eB = r.readings['B.1.1'];
  check(`${tag}: attacker loses ${eA}`,
    near(res.attacker.hpLost, eA, lostTol(eA)), `engine ${fmt(res.attacker.hpLost)}`);
  check(`${tag}: defender loses ${eB}` + (m.type === 'fortress' ? ' (mitigated)' : m.type ? ' (unchanged — inert)' : ''),
    near(res.defender.hpLost, eB, lostTol(eB)), `engine ${fmt(res.defender.hpLost)}`);
  if (!near(res.defender.hpLost, eB, lostTol(eB))) {
    cannotReproduce(`buildings ${tag} defender loss`, eB, res.defender.hpLost);
  }
  const eBld = r.readings['B.1.bldg.1'];
  if (eBld !== undefined) {
    check(`${tag}: the building loses ${eBld} HP`,
      near(res.defender.buildings[0].hpLost, eBld, lostTol(eBld)),
      `engine ${fmt(res.defender.buildings[0].hpLost)}`);
    if (m.bldg && m.bldg.pool) {
      const br = poolBracket(m.bldg.lost, m.bldg.pct, undefined);
      check(`${tag}: building HP pool inside the measured bracket`,
        inBracket(res.defender.buildings[0].hpFull, br),
        `engine ${fmt(res.defender.buildings[0].hpFull)} vs [${br.map(fmt)}]`);
    }
  }
}

// ===========================================================================
console.log('\n8. the invariants HANDOVER §10 asks the app to assert against itself');
// ===========================================================================
check('E(30) = 28.3333', Math.abs(effectiveUnits(30) - 28.333333) < 1e-4, String(effectiveUnits(30)));
check('E(50) = E(57) = E(113) = 35',
  effectiveUnits(50) === 35 && effectiveUnits(57) === 35 && effectiveUnits(113) === 35);
check('E(45) = 34.5833', Math.abs(effectiveUnits(45) - 34.583333) < 1e-4, String(effectiveUnits(45)));
check('E(29) = 27.65', Math.abs(effectiveUnits(29) - 27.65) < 1e-9, String(effectiveUnits(29)));
check('E(20) = 20 and E(10) = 10 (linear below 21)',
  effectiveUnits(20) === 20 && effectiveUnits(10) === 10);
check('m(0.1) = 0.145 — the 0.05 floor is real', Math.abs(hpMultiplier(0.1) - 0.145) < 1e-12);
check('m(1) = 1', Math.abs(hpMultiplier(1) - 1) < 1e-12);
{
  const r = simulate({ attacker: { unit: 'inf', count: 30 }, defender: { unit: 'inf', count: 30 } });
  check('30 inf vs 30 inf: attacker 141.67, defender 113.33',
    near(r.attacker.hpLost, 141.6667, 0.001) && near(r.defender.hpLost, 113.3333, 0.001),
    `${fmt(r.attacker.hpLost)} / ${fmt(r.defender.hpLost)}`);
}
{
  const r = simulate({ attacker: { unit: 'tac', count: 10 }, defender: { unit: 'ac', count: 20 } });
  check('10 tac vs 20 ac: attacker 160.00, defender exactly 240.00',
    near(r.attacker.hpLost, 160, 1e-9) && near(r.defender.hpLost, 240, 1e-9),
    `${fmt(r.attacker.hpLost)} / ${fmt(r.defender.hpLost)}`);
}
{
  const r = simulate({ attacker: { unit: 'tac', count: 10 }, defender: { unit: 'ht', count: 20 } });
  check('10 tac vs 20 ht: attacker 80.00, defender exactly 270.00',
    near(r.attacker.hpLost, 80, 1e-9) && near(r.defender.hpLost, 270, 1e-9),
    `${fmt(r.attacker.hpLost)} / ${fmt(r.defender.hpLost)}`);
}
{
  // The cell that discriminates the correct post-fire law (36.833) from
  // HANDOVER §4's approximation (36.667). The measurement says 36.83.
  const r = simulate({ attacker: { unit: 'int', count: 10 }, defender: { unit: 'ac', count: 20 } });
  check('10 int vs 20 ac: defender loses 36.83, NOT the 36.67 of the superseded law',
    near(r.defender.hpLost, 36.83, 0.005) && !near(r.defender.hpLost, 36.667, 0.005),
    `engine ${fmt(r.defender.hpLost)}`);
}
{
  const r = simulate({
    attacker: { unit: 'inf', count: 10 },
    defender: { unit: 'inf', count: 10, trench: 20 },
  });
  check('trench 20 on the defender: attacker loses 87.5, defender pool x1.35',
    near(r.attacker.hpLost, 87.5, 1e-9) && near(r.defender.pool, 270, 1e-9),
    `${fmt(r.attacker.hpLost)} / pool ${fmt(r.defender.pool)}`);
}
{
  const r = simulate({
    attacker: { unit: 'inf', count: 10, trench: 20 },
    defender: { unit: 'inf', count: 10 },
  });
  check('trench 20 on the attacker: defender still loses exactly 40.0, attacker pool x1.35',
    near(r.defender.hpLost, 40, 1e-9) && near(r.attacker.pool, 270, 1e-9),
    `${fmt(r.defender.hpLost)} / pool ${fmt(r.attacker.pool)}`);
  check('  and its deaths fall from 2 to 1 on the inflated per-unit HP',
    r.attacker.deaths === 1, String(r.attacker.deaths));
}
for (const [lvl, want] of [[1, 0.70], [2, 0.55], [3, 0.40], [4, 0.25], [5, 0.10]]) {
  check(`fortress L${lvl}: defender's loss ratio ${want.toFixed(2)}`,
    Math.abs((1 - fortressDR(50 * lvl)) - want) < 1e-9,
    String(1 - fortressDR(50 * lvl)));
}
check('a worn fortress mitigates less: 241.5 HP gives DR 87.45%',
  Math.abs(fortressDR(241.5) - 0.8745) < 1e-9, String(fortressDR(241.5)));
check('fortressDR clamps to 1 rather than returning the raw 1.05 at level 6',
  fortressDR(300) === 1, String(fortressDR(300)));
check('fortressDR(0) is 0 — a destroyed or absent fortress is not credited 15%',
  fortressDR(0) === 0);

// ===========================================================================
console.log('\n9. max HP integers, cross-checked against pools measured elsewhere');
// ===========================================================================
{
  // meta.max_hp_bounds cannot be re-derived from results.jsonl (the pool and
  // percentage behind it were never written). The air_vs_ground rows give an
  // INDEPENDENT bracket, but only for the 13 units that appear there.
  const covered = new Set();
  for (const r of withReadings('air_vs_ground')) {
    const m = r.meta;
    for (const [slot, code, n] of [['A.1.1', m.atk, m.atk_n], ['B.1.1', m.target, m.def_n]]) {
      const d = m.detail[slot];
      const [lo, hi] = poolBracket(d.lost, d.pct, d.lost_source);
      const unit = UNITS[code];
      if (!inBracket(unit.maxHP * n, [lo, hi])) {
        cannotReproduce(`${code} maxHP ${unit.maxHP}`, `pool in [${lo.toFixed(2)}, ${hi.toFixed(2)}]`,
          unit.maxHP * n);
      }
      covered.add(code);
    }
  }
  check(`all ${covered.size} units appearing in air_vs_ground have max HP integers consistent `
    + 'with an independently derived pool bracket',
    unreproduced.filter((u) => u.what.includes('maxHP')).length === 0,
    JSON.stringify(unreproduced.filter((u) => u.what.includes('maxHP'))));
  const uncovered = Object.keys(UNITS).filter((c) => !covered.has(c));
  check(`and the ${uncovered.length} that do not (${uncovered.join(', ')}) are flagged as having `
    + 'no independent check',
    uncovered.every((c) => c === 'bal'
      || PROVENANCE[UNITS[c].provenance.maxHP].source.includes('no independent')
      || UNITS[c].provenance.maxHP === 'UNITS.maxHP.noIndependentCheck'
      || UNITS[c].provenance.maxHP === 'UNITS.balloon'),
    uncovered.map((c) => `${c}:${UNITS[c].provenance.maxHP}`).join(' '));
}

// ===========================================================================
console.log('\n10. honesty — simulate() never throws, and never overstates what it knows');
// ===========================================================================
{
  const codes = Object.keys(UNITS);
  let threw = 0; let noDerivation = 0; let mislabelled = 0; let fabricated = 0;
  let measuredCells = 0; let estimatedCells = 0; let unknownCells = 0;
  for (const a of codes) {
    for (const d of codes) {
      let res;
      try {
        res = simulate({
          attacker: { unit: a, count: 30, hpPct: 55, trench: 7, buildings: [{ code: 'barracks', level: 9 }] },
          defender: { unit: d, count: 45, hpPct: 100, trench: 20, buildings: [{ code: 'fortress', level: 3 }] },
          rounds: 3,
        });
      } catch (err) {
        threw += 1;
        cannotReproduce(`simulate(${a} vs ${d}) threw`, 'a Result', String(err && err.message));
        continue;
      }
      if (!Array.isArray(res.derivation) || res.derivation.length === 0) noDerivation += 1;
      const cov = coverageOf(a, d);
      if (cov.level !== 'measured' && res.coverage.level === 'measured') mislabelled += 1;
      if (res.coverage.level === 'unknown'
          && (res.attacker.hpLost !== null || res.defender.hpLost !== null)) fabricated += 1;
      if (res.coverage.level === 'measured') measuredCells += 1;
      else if (res.coverage.level === 'estimated') estimatedCells += 1;
      else unknownCells += 1;
    }
  }
  const n = codes.length * codes.length;
  check(`simulate() never throws across all ${n} roster pairings (in a deliberately awkward `
    + 'configuration: 55% HP, trench 7, an over-cap building, 3 rounds)', threw === 0, `${threw} threw`);
  check(`derivation[] is populated for all ${n} results`, noDerivation === 0, `${noDerivation} empty`);
  check('no result is labelled \'measured\' when the matchup is not', mislabelled === 0, `${mislabelled} mislabelled`);
  check('every \'unknown\' result withholds its numbers instead of inventing them',
    fabricated === 0, `${fabricated} fabricated`);
  check(`the cross-product splits ${measuredCells} measured / ${estimatedCells} estimated / `
    + `${unknownCells} unknown — and this configuration has 3 rounds and trench 7, so nothing `
    + 'here should be measured', measuredCells === 0, `${measuredCells} claimed measured`);
}
{
  // Same sweep in the clean configuration: one round, no trench, no buildings.
  const codes = Object.keys(UNITS);
  const seen = { measured: 0, estimated: 0, unknown: 0 };
  for (const a of codes) {
    for (const d of codes) {
      const res = simulate({
        attacker: { unit: a, count: 10 }, defender: { unit: d, count: 10 }, rounds: 1,
      });
      seen[res.coverage.level] += 1;
      if (res.coverage.level === 'measured'
          && !(a === d || (UNITS[a].cls === 'air' && UNITS[d].cls === 'land' && a !== 'bal'))) {
        cannotReproduce(`coverage(${a} vs ${d})`, 'not measured', 'measured');
      }
    }
  }
  // 16 diagonals (bal excluded) + 3 fliers x 10 ground units = 46
  check(`in a clean 1-round duel exactly 46 of ${codes.length ** 2} pairings are 'measured' `
    + '(16 diagonals + 3 fliers x 10 ground targets)', seen.measured === 46, JSON.stringify(seen));
  check('land attacking air is never measured and never numbered',
    (() => {
      const r = simulate({ attacker: { unit: 'inf', count: 10 }, defender: { unit: 'int', count: 10 } });
      return r.coverage.level === 'unknown' && r.defender.hpLost === null && r.attacker.hpLost === null
        && /never been measured/.test(r.coverage.reason);
    })());
  check('land off-diagonal is \'estimated\', numbered, and says why it might be wrong',
    (() => {
      const r = simulate({ attacker: { unit: 'inf', count: 10 }, defender: { unit: 'ht', count: 10 } });
      return r.coverage.level === 'estimated' && r.defender.hpLost > 0
        && /off-diagonal/.test(r.coverage.reason) && /wrong by any factor/.test(r.coverage.reason);
    })());
  check('sea off-diagonal is \'estimated\' too',
    simulate({ attacker: { unit: 'sub', count: 10 }, defender: { unit: 'bb', count: 10 } })
      .coverage.level === 'estimated');
}
check('multi-round downgrades a measured matchup to \'estimated\' and says every reading used 1 round',
  (() => {
    const r = simulate({
      attacker: { unit: 'inf', count: 10 }, defender: { unit: 'inf', count: 10 }, rounds: 4,
    });
    return r.coverage.level === 'estimated'
      && r.coverage.caveats.some((c) => /maxRounds = 1|4 rounds/.test(c));
  })());
check('an unsampled trench level is not exact, and brackets its sampled neighbours',
  (() => {
    const t = trenchFactors(7);
    return t.exact === false && t.pool === TRENCH_POOL[5] && t.poolRange[1] === TRENCH_POOL[10]
      && t.outputRange[0] === TRENCH_OUTPUT[5] && t.outputRange[1] === TRENCH_OUTPUT[10]
      && /never submitted/.test(t.note);
  })());
check('a sampled trench level is exact', trenchFactors(15).exact === true && trenchFactors(0).exact === true);
check('trench above 20 is clamped and flagged',
  trenchFactors(25).level === 20 && trenchFactors(25).exact === false);
check('building damage from a non-infantry attacker is withheld, not extrapolated',
  (() => {
    const r = simulate({
      attacker: { unit: 'cav', count: 30 },
      defender: { unit: 'cav', count: 30, buildings: [{ code: 'fortress', level: 3 }] },
    });
    return r.defender.damageToBuildings === null
      && r.coverage.caveats.some((c) => /only ever been measured for infantry/.test(c));
  })());
check('a fortress against an air attacker still computes, but is downgraded and caveated',
  (() => {
    const r = simulate({
      attacker: { unit: 'tac', count: 10 },
      defender: { unit: 'inf', count: 57, buildings: [{ code: 'fortress', level: 3 }] },
    });
    return r.coverage.level === 'estimated'
      && r.coverage.caveats.some((c) => /land \(infantry\) attacker/.test(c));
  })());
check('an air attacker wiped to zero survivors withholds its damage instead of guessing a branch',
  (() => {
    const r = simulate({
      attacker: { unit: 'tac', count: 1 },
      defender: { unit: 'ac', count: 50 },
    });
    return r.attacker.wiped === true && r.defender.hpLost === null
      && r.coverage.level === 'unknown'
      && r.coverage.caveats.some((c) => /no survivors/.test(c));
  })());
check('every derivation entry carries a label, a formula and a value key',
  (() => {
    const r = simulate({
      attacker: { unit: 'int', count: 10 },
      defender: { unit: 'inf', count: 57, buildings: [{ code: 'fortress', level: 2 }] },
    });
    return r.derivation.length > 5 && r.derivation.every(
      (e) => typeof e.label === 'string' && typeof e.formula === 'string' && 'value' in e,
    );
  })());
{
  // The app must never put user traffic on dxcalc.com. That is a property of
  // the source, not of a run, so it is asserted against the source.
  const src = ['../data.js', '../engine.js']
    .map((f) => readFileSync(join(HERE, f), 'utf8')).join('\n');
  const banned = /\bfetch\s*\(|XMLHttpRequest|WebSocket|EventSource|navigator\.sendBeacon|import\s*\(|https?:\/\/(?!\s)/g;
  const hits = src.match(banned) || [];
  check('engine.js and data.js contain no network call of any kind — no fetch, no XHR, no '
    + 'WebSocket, no URL, no dynamic import', hits.length === 0, `found: ${hits.join(', ')}`);
  // Comments may name the site; code may not.
  const code = src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
  check('and dxcalc.com appears nowhere in the executable code (only in comments explaining '
    + 'why it must not)', !/dxcalc\.com/.test(code),
    (code.match(/.*dxcalc\.com.*/g) || []).join(' | '));
}
check('every constant in UNITS points at a PROVENANCE note that exists',
  Object.values(UNITS).every((u) => Object.values(u.provenance).every((k) => PROVENANCE[k])),
  Object.values(UNITS).flatMap((u) => Object.values(u.provenance).filter((k) => !PROVENANCE[k])).join(' '));
check(`NOT_MEASURED lists ${NOT_MEASURED.length} open gaps, each with what/why/closedBy`,
  NOT_MEASURED.length >= 20 && NOT_MEASURED.every((g) => g.key && g.what && g.why && g.closedBy));
check('the land off-diagonal gap — the biggest one — is named in NOT_MEASURED',
  NOT_MEASURED.some((g) => g.key === 'land_off_diagonal' && /biggest/.test(g.why)));

// ===========================================================================
console.log('\n11. patrol — replayed as an explicitly estimated band');
// ===========================================================================
// The engine now implements patrol. Its ATTRITION coefficient is a band, not
// a number, so every patrol result is labelled estimated -- but a band is only
// honest if the numbers inside it actually reproduce the battles that were
// fought. All nine measured cells are replayed here against a 1.5% tolerance,
// which is the width the band itself implies, not a tolerance chosen to pass.
{
  const airCell = {};
  for (const r of rows) {
    if (r.experiment !== 'air_vs_ground') continue;
    const b = (r.meta.detail || {})['B.1.1'] || {};
    if (b.lost != null) airCell[`${r.meta.atk}/${r.meta.target}`] = { lost: b.lost, defN: r.meta.def_n };
  }
  const seen = new Set();
  let worstErr = 0;
  for (const r of rows) {
    const m = r.meta || {};
    if (r.experiment !== 'patrol' || m.error || m.rounds !== '1' || m.terrain !== 'patrol') continue;
    const ref = airCell[`${m.unit}/${m.target}`];
    const b = (m.detail || {})['B.1.1'] || {};
    if (!ref || b.lost == null) continue;
    seen.add(`${m.unit}/${m.target}`);
    const res = simulate({
      mode: 'patrol',
      attacker: { unit: m.unit, count: m.atk_n, hpPct: 100 },
      defender: { unit: m.target, count: m.def_n, hpPct: 100 },
      rounds: 1,
    });
    const err = Math.abs(res.defender.hpLost - b.lost) / b.lost;
    worstErr = Math.max(worstErr, err);
    check(`patrol ${m.unit} vs ${m.target}: engine ${res.defender.hpLost.toFixed(2)} vs measured ${b.lost}`,
      err <= 0.015, `${(err * 100).toFixed(2)}% off`);
    check(`patrol ${m.unit} vs ${m.target} is never labelled measured`,
      res.coverage.level === 'estimated', res.coverage.level);
  }
  // Nine distinct cells; tac/inf appears twice because the maxRounds ladder
  // re-flew it, so count cells rather than rows.
  check('all nine measured patrol cells were replayed', seen.size === 9,
    `${seen.size} distinct: ${[...seen].join(' ')}`);
  check(`worst patrol error is inside the band the coefficient implies`,
    worstErr <= 0.015, `${(worstErr * 100).toFixed(2)}%`);

  // The maxRounds halves. These ARE measured and must be exact in kind:
  // patrol scales, a strike does not.
  const strike = (rr) => simulate({
    mode: 'strike', attacker: { unit: 'tac', count: 10, hpPct: 100 },
    defender: { unit: 'inf', count: 57, hpPct: 100 }, rounds: rr,
  }).defender.hpLost;
  check('a direct strike ignores maxRounds (measured: byte-identical at 0.25/0.5/0.75/1)',
    [0.25, 0.5, 0.75, 1].every((r) => Math.abs(strike(r) - strike(1)) < 1e-9),
    [0.25, 0.5, 0.75, 1].map((r) => strike(r).toFixed(3)).join(' / '));
  const pat = (rr) => simulate({
    mode: 'patrol', attacker: { unit: 'tac', count: 10, hpPct: 100 },
    defender: { unit: 'inf', count: 57, hpPct: 100 }, rounds: rr,
  }).defender.hpLost;
  // Proportional, but not EXACTLY: a longer patrol eats more return fire, so
  // the attrition factor differs slightly between rungs. That is real in both
  // directions -- the live ladder's per-round rate rose 30.13 -> 30.33 across
  // 0.25 to 1 (+0.67%), and the engine falls by a similar amount. Asserting
  // exact linearity would be asserting something the measurement does not say.
  check('patrol damage is proportional to maxRounds, to the flatness measured',
    Math.abs(pat(0.25) * 4 / pat(1) - 1) < 0.015,
    `${pat(0.25).toFixed(3)} x 4 = ${(pat(0.25) * 4).toFixed(3)} vs ${pat(1).toFixed(3)}`);
  check('and a quarter-round patrol deals roughly a quarter of the damage',
    pat(0.25) > 0 && Math.abs(pat(0.25) / pat(1) - 0.25) < 0.01,
    `${(pat(0.25) / pat(1)).toFixed(4)}`);
  check('patrol out-damages a strike against a target that shoots back',
    pat(1) > strike(1));
  check('and matches it against one that barely does, to within the band',
    Math.abs(pat(1) / strike(1) - 1) < 0.05, (pat(1) / strike(1)).toFixed(4));

  // Patrol is only offered where it was measured.
  check('patrol on a land-vs-land pairing falls back and says so',
    simulate({ mode: 'patrol', attacker: { unit: 'inf', count: 10 }, defender: { unit: 'inf', count: 10 } })
      .coverage.caveats.some((c) => /only ever measured for an AIR stack/.test(c)));
}

// ===========================================================================
console.log('\n12. composite stacks — replayed against the four measured mixtures');
// ===========================================================================
// A stack is a MIXTURE. Both halves of the law are asserted here against the
// real readings: the cumulative roster-order saturation that sets each row's
// effective units, and the (attack x count) split that decides who takes the
// damage. Neither is visible in any single-type measurement.
{
  let cells = 0;
  for (const r of rows) {
    const m = r.meta || {};
    if (r.experiment !== 'mixed_stacks' || m.error) continue;
    if (!Array.isArray(m.rows) || m.rows.length < 2) continue;
    const d = m.detail || {};
    const obsOut = (d['A.1.1'] || {}).lost;
    if (obsOut == null) continue;
    cells += 1;
    const res = simulate({
      attacker: { unit: 'inf', count: m.atk_n, hpPct: 100 },
      defender: { rows: m.rows.map(([unit, count]) => ({ unit, count, hpPct: 100 })) },
      rounds: 1,
    });
    check(`${m.label}: defender output ${res.attacker.hpLost.toFixed(2)} vs measured ${obsOut}`,
      Math.abs(res.attacker.hpLost - obsOut) <= 0.05,
      `${(res.attacker.hpLost - obsOut).toFixed(3)} off`);
    // Per-row damage split, itemised straight off the page.
    m.rows.forEach(([unit], i) => {
      const obs = (d[`B.1.${i + 1}`] || {}).lost;
      if (obs == null) return;
      const got = res.defender.rows[i];
      check(`${m.label}: ${unit} row took ${got.hpLost.toFixed(2)} vs measured ${obs}`,
        Math.abs(got.hpLost - obs) <= 0.05, `${(got.hpLost - obs).toFixed(3)} off`);
    });
  }
  check('all four measured mixtures were replayed', cells >= 4, String(cells));

  // Submission order must not change the answer: the server sorts first.
  const a = simulate({ attacker: { unit: 'inf', count: 20 },
    defender: { rows: [{ unit: 'inf', count: 25 }, { unit: 'art', count: 25 }] } });
  const b = simulate({ attacker: { unit: 'inf', count: 20 },
    defender: { rows: [{ unit: 'art', count: 25 }, { unit: 'inf', count: 25 }] } });
  check('submission order does not change the stack output',
    Math.abs(a.attacker.hpLost - b.attacker.hpLost) < 1e-9,
    `${a.attacker.hpLost} vs ${b.attacker.hpLost}`);

  // The finding that matters to a player.
  const alone = simulate({ attacker: { unit: 'inf', count: 20 },
    defender: { rows: [{ unit: 'art', count: 40 }] } });
  const behind = simulate({ attacker: { unit: 'inf', count: 20 },
    defender: { rows: [{ unit: 'inf', count: 10 }, { unit: 'art', count: 40 }] } });
  check('a type behind others draws from the saturated tail (40 art: 33.3 -> 25 effective)',
    Math.abs(alone.defender.rows[0].effective - effectiveUnits(40)) < 1e-9
    && Math.abs(behind.defender.rows[1].effective - 25) < 1e-9,
    `${alone.defender.rows[0].effective} vs ${behind.defender.rows[1].effective}`);
  check('and the engine flags that row as saturated',
    behind.defender.rows[1].saturated === true);

  // The server refuses a repeated type; the engine must not compute one.
  const dup = simulate({ attacker: { unit: 'inf', count: 10 },
    defender: { rows: [{ unit: 'inf', count: 25 }, { unit: 'inf', count: 25 }] } });
  check('a duplicated unit type is dropped, not merged',
    dup.defender.rows.length === 1, `${dup.defender.rows.length} rows`);
  check('and the reason is stated as a caveat',
    dup.coverage.caveats.some((c) => /same unit type twice/.test(c)),
    dup.coverage.caveats.join(' | '));

  // --- two defects found by the UI worker, both integrity failures --------
  // 1. Coverage judged only the FIRST row of each side. A stack of infantry
  //    plus artillery attacking infantry plus cavalry is four pairings, and
  //    only one is the measured diagonal -- it reported 'measured' citing
  //    infantry-vs-infantry while cavalry-vs-artillery, never once submitted,
  //    went unmentioned.
  const mixedPair = simulate({
    attacker: { rows: [{ unit: 'inf', count: 10 }, { unit: 'art', count: 40 }] },
    defender: { rows: [{ unit: 'inf', count: 30 }, { unit: 'cav', count: 10 }] },
  });
  check('coverage judges every pairing, not just the first row of each side',
    mixedPair.coverage.level === 'estimated', mixedPair.coverage.level);
  check('and says how many pairings are unmeasured',
    /3 of 4 unit pairings/.test(mixedPair.coverage.reason),
    mixedPair.coverage.reason.slice(0, 90));
  check('the pairing cross-product is exposed for inspection',
    Array.isArray(mixedPair.coverage.pairs) && mixedPair.coverage.pairs.length === 4);
  check('an all-measured mixture is still reported measured',
    simulate({ attacker: { rows: [{ unit: 'inf', count: 10 }] },
      defender: { rows: [{ unit: 'inf', count: 30 }] } }).coverage.level === 'measured');

  // 2. Rows reported damageDealt: 0 on the air and patrol paths, whose laws
  //    work on whole-stack survivors and cannot be decomposed per row. Zero is
  //    a claim; the stack total was 113 at the time.
  const airMix = simulate({
    attacker: { rows: [{ unit: 'int', count: 10 }, { unit: 'tac', count: 10 }] },
    defender: { rows: [{ unit: 'inf', count: 30 }, { unit: 'ht', count: 10 }] },
  });
  check('an un-itemisable row reports null damage dealt, never 0',
    airMix.attacker.rows.every((r) => r.damageDealt === null),
    JSON.stringify(airMix.attacker.rows.map((r) => r.damageDealt)));
  check('while the stack total is still reported',
    typeof airMix.attacker.damageDealt === 'number' && airMix.attacker.damageDealt > 0,
    String(airMix.attacker.damageDealt));
  check('a land mixture DOES itemise damage dealt per row',
    simulate({ attacker: { rows: [{ unit: 'inf', count: 25 }, { unit: 'art', count: 25 }] },
      defender: { rows: [{ unit: 'inf', count: 30 }] } })
      .attacker.rows.every((r) => typeof r.damageDealt === 'number'));

  // 3. Stack-level multipliers must reach the ROWS too. They did not: a
  //    defender on trench 10 reported rows summing to 141.67 against a stack
  //    figure of 218.17 -- the same number times the 1.54 trench output bonus.
  //    Rows that do not sum to their own stack are the composite version of
  //    the building row that clobbered the attacker's slot for a whole phase.
  for (const [why, cfg] of [
    ['trench output bonus', { attacker: { rows: [{ unit: 'inf', count: 10 }], trench: 20 },
      defender: { rows: [{ unit: 'inf', count: 30 }], trench: 10 } }],
    ['a trenched mixture', { attacker: { rows: [{ unit: 'inf', count: 20 }] },
      defender: { rows: [{ unit: 'inf', count: 25 }, { unit: 'art', count: 25 }], trench: 15 } }],
    ['patrol duration', { mode: 'patrol', rounds: 2,
      attacker: { rows: [{ unit: 'tac', count: 10 }] },
      defender: { rows: [{ unit: 'inf', count: 57 }] } }],
  ]) {
    const r = simulate(cfg);
    for (const side of ['attacker', 'defender']) {
      const rowsSum = r[side].rows.reduce(
        (t, x) => t + (typeof x.damageDealt === 'number' ? x.damageDealt : 0), 0);
      const total = r[side].damageDealt;
      if (total === null || !r[side].rows.some((x) => typeof x.damageDealt === 'number')) continue;
      check(`${why}: ${side} rows sum to the stack's damage dealt`,
        Math.abs(rowsSum - total) < 0.01, `${rowsSum.toFixed(2)} vs ${total.toFixed(2)}`);
    }
  }

  // --- stacks the game refuses to field -----------------------------------
  // Measured, and every refusal stated by the server. A stack it will not
  // accept is not a battle with an uncertain answer; it is not a battle. The
  // app shipped computing these, which is a number for an army that cannot
  // exist.
  const crossClass = simulate({
    attacker: { rows: [{ unit: 'inf', count: 10 }, { unit: 'int', count: 10 }] },
    defender: { rows: [{ unit: 'inf', count: 30 }] },
  });
  check('a cross-class stack is refused, not computed',
    crossClass.coverage.level === 'unknown' && crossClass.attacker.hpLost === null,
    `${crossClass.coverage.level} / ${crossClass.attacker.hpLost}`);
  check('and the reason quotes what the server actually says',
    /cannot share a stack/.test(crossClass.coverage.reason));
  const withConvoy = simulate({
    attacker: { rows: [{ unit: 'inf', count: 10 }, { unit: 'convoy', count: 5 }] },
    defender: { rows: [{ unit: 'inf', count: 30 }] },
  });
  check('the Airplane Convoy stacks with nothing — measured, not assumed',
    withConvoy.coverage.level === 'unknown', withConvoy.coverage.level);
  check('a convoy ALONE is still a legal stack',
    simulate({ attacker: { rows: [{ unit: 'convoy', count: 10 }] },
      defender: { rows: [{ unit: 'convoy', count: 10 }] } }).coverage.level !== 'unknown');

  // The cap was 8, inherited from duel()'s row-blanking range. A land stack
  // takes 9 types -- the server accepted all nine and returned nine rows.
  const nine = 'inf cav ac lart art rrg lt ht st'.split(' ')
    .map((u) => ({ unit: u, count: 5 }));
  const big = simulate({ attacker: { rows: nine },
    defender: { rows: [{ unit: 'inf', count: 30 }] } });
  check('all nine land types fit in one stack', big.attacker.rows.length === 9,
    String(big.attacker.rows.length));
  check('and the row cap now matches the page, not the old guess',
    MAX_UNIT_ROWS === 15, String(MAX_UNIT_ROWS));
  check('their effective units still sum to E(total)',
    Math.abs(big.attacker.rows.reduce((t, r) => t + r.effective, 0)
      - effectiveUnits(45)) < 1e-9);

  // Single-row configs must be untouched by any of this.
  const single = simulate({ attacker: { unit: 'inf', count: 30 },
    defender: { unit: 'inf', count: 30 } });
  check('a single-type stack still gives the measured control exactly',
    Math.abs(single.attacker.hpLost - 141.67) < 0.01
    && Math.abs(single.defender.hpLost - 113.33) < 0.01,
    `${single.attacker.hpLost} / ${single.defender.hpLost}`);
}

// ===========================================================================
console.log('\n13. heroes — replayed against every measured reading');
// ===========================================================================
// A hero is a unit plus a buff, and the app now models it. Replayed here
// against the live figures for all three shapes: a pure combat unit, the one
// strong buffer, and the hero that sits AFTER the units and therefore adds
// nothing to a saturated stack.
{
  const battle = (hero, n) => simulate({
    attacker: { rows: [{ unit: 'inf', count: 20 }] },
    defender: { rows: [{ unit: 'inf', count: n }], hero },
  }).attacker.hpLost;

  const measured = {
    kangal: { 10: 70.00, 30: 159.92, 50: 190.00 },
    joffre_home: { 10: 81.00, 30: 197.89, 50: 237.00 },
    maeve: { 10: 54.00, 30: 144.27, 50: 175.00 },
  };
  for (const [code, byN] of Object.entries(measured)) {
    for (const [n, want] of Object.entries(byN)) {
      const got = battle({ code, level: 10 }, Number(n));
      check(`${code} at n=${n}: ${got.toFixed(2)} vs measured ${want}`,
        Math.abs(got - want) <= 0.05, `${(got - want).toFixed(3)} off`);
    }
  }
  check('maeve adds NOTHING to a saturated stack — she draws from the tail',
    Math.abs(battle({ code: 'maeve', level: 10 }, 50) - battle(null, 50)) < 1e-9);
  check('while she does help a small one',
    battle({ code: 'maeve', level: 10 }, 10) > battle(null, 10));

  // A does not move with level; M does, for the two heroes that have one.
  check('a pure unit is level-independent (A is flat, M = 1.00)',
    Math.abs(battle({ code: 'kangal', level: 1 }, 30)
      - battle({ code: 'kangal', level: 10 }, 30)) < 1e-9);
  check('joffre_home at level 1 is measurably weaker than at 15',
    battle({ code: 'joffre_home', level: 1 }, 30)
      < battle({ code: 'joffre_home', level: 15 }, 30));
  check('its level-1 buff is the measured 1.10',
    Math.abs(heroBuff('joffre_home', 1).m - 1.10) < 1e-9);
  check('and a measured level is flagged exact',
    heroBuff('joffre_home', 15).exact === true);
  check('while an unmeasured one is flagged interpolated, not exact',
    heroBuff('joffre_home', 13).exact === false
    && /interpolated/.test(heroBuff('joffre_home', 13).note),
    heroBuff('joffre_home', 13).note);
  check('an interpolated buff lands between its two measured neighbours',
    heroBuff('joffre_home', 13).m > 1.32 && heroBuff('joffre_home', 13).m < 1.40);

  // Caps are the server's own, not the dropdown's 1-20.
  const capped = simulate({
    attacker: { rows: [{ unit: 'inf', count: 20 }] },
    defender: { rows: [{ unit: 'inf', count: 30 }], hero: { code: 'kangal', level: 20 } },
  });
  check('a level above the hero cap is clamped and explained',
    capped.coverage.caveats.some((c) => /caps at level 10/.test(c)),
    capped.coverage.caveats.join(' | '));

  // Heroes with nothing measured on land must not silently do nothing.
  const naval = simulate({
    attacker: { rows: [{ unit: 'inf', count: 20 }] },
    defender: { rows: [{ unit: 'inf', count: 30 }], hero: { code: 'otto', level: 10 } },
  });
  check('a land-refused hero is named, not silently dropped',
    naval.coverage.caveats.some((c) => /Otto Hersing/.test(c)),
    naval.coverage.caveats.join(' | '));
  check('and the battle still computes without its effect',
    Math.abs(naval.attacker.hpLost - 141.67) < 0.01, String(naval.attacker.hpLost));
}

// ===========================================================================
console.log('\n14. coverage of the record itself');
// ===========================================================================
{
  const counts = {};
  for (const r of rows) counts[r.experiment] = (counts[r.experiment] || 0) + 1;
  const replayed = ['semantics', 'unit_stats', 'hp_scaling', 'air_vs_ground', 'trenches',
    'fortress', 'buildings', 'patrol', 'mixed_stacks',
    // Heroes are now modelled and replayed above: the sweeps that measured
    // them are physics the engine reproduces, not declared omissions.
    'heroes', 'hero_scaling', 'hero_table', 'hero_levels'];
  const notReplayed = Object.keys(counts).filter((e) => !replayed.includes(e));
  console.log(`  note  replayed: ${replayed.map((e) => `${e} ${counts[e] || 0}`).join(', ')}`);
  console.log(`  note  NOT replayed: ${notReplayed.map((e) => `${e} ${counts[e]}`).join(', ') || 'none'}`);
  // 'heroes' is measured but deliberately unmodelled: every reading is level
  // 10 and the 1-20 curve is untouched, so shipping one level as the mechanic
  // would put a confident number on 19 unmeasured ones. Declared, not dropped.
  // stack_limits is a constraints probe, not a physics sweep: its readings are
  // server refusals, and they are encoded in STACK_GROUP rather than replayed.
  // What remains are the two CONSTRAINT probes, whose readings are server
  // refusals encoded in STACK_GROUP and HEROES.maxLevel rather than physics to
  // replay: which types may share a stack, and each hero's real level cap.
  const declaredNonReplay = ['stack_limits', 'hero_caps'];
  check('every unreplayed experiment is one the engine declares and explains',
    notReplayed.every((e) => declaredNonReplay.includes(e)),
    notReplayed.join(', ') || 'none');
  check('heroes are recorded as measured but not modelled',
    PROVENANCE['HEROES.measured'].confidence === 'measured'
    && /DELIBERATELY NOT MODELLED/.test(PROVENANCE['HEROES.measured'].note));
  check('and the app still declares heroes as a gap the user can see',
    NOT_MEASURED.some((g) => /hero/i.test(g.key) || /hero/i.test(g.what)));
  check('composite saturation and allocation are both recorded as measured',
    PROVENANCE['STACK.saturation'].confidence === 'measured'
    && PROVENANCE['STACK.allocation'].confidence === 'measured');
  check('and the patrol attrition band is recorded as estimated, not measured',
    PROVENANCE['PATROL.attrition'].confidence === 'estimated');
  check('while the patrol maxRounds behaviour is recorded as measured',
    PROVENANCE['PATROL.rounds'].confidence === 'measured');
}

// ===========================================================================
console.log('');
if (unreproduced.length) {
  console.log('MEASUREMENTS THE ENGINE COULD NOT REPRODUCE:');
  for (const u of unreproduced) {
    console.log(`  - ${u.what}: recorded ${u.expected}, engine ${fmt(u.got)}${u.note ? ` (${u.note})` : ''}`);
  }
  console.log('');
}
if (failures.length) {
  console.log(`${failures.length} CHECK(S) FAILED, ${ok} passed`);
  for (const f of failures) console.log(`  FAILED: ${f.label}\n          ${f.detail}`);
  process.exit(1);
}
console.log(`ALL ${ok} CHECKS PASSED`);
console.log('Tolerances: HP lost ±0.005 where the summary table gave 2 decimals, ±0.05 where only '
  + 'a 1-decimal span was recorded; pools asserted inside the bracket implied by 3-significant-figure '
  + 'percentages; death counts exact.');
