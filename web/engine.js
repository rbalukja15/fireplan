// web/engine.js — the recovered dxcalc/s1914 combat model, implemented locally.
//
// Pure functions. No DOM, no network, no dependencies. This module NEVER
// contacts dxcalc.com: it is a clean-room implementation of measured game
// mechanics, and putting user traffic on one person's ad-supported fan site
// is exactly what it exists to avoid.
//
// Two rules govern everything here, from HANDOVER.md §0:
//
//   1. simulate() never throws, for any roster combination.
//   2. A number the record cannot support is either flagged or withheld —
//      never emitted as if it were measured. A confident wrong answer is the
//      failure mode this project keeps hitting; six separate rig defects
//      produced plausible wrong numbers, and five of them reported something
//      FALSE with confidence rather than reporting nothing.
//
// derivation[] is a first-class output, not a debug aid. Every number the UI
// shows should be traceable through it.

import {
  UNITS,
  BUILDINGS,
  TRENCH_POOL,
  TRENCH_POOL_BRACKET,
  TRENCH_OUTPUT,
  TRENCH_SAMPLED_LEVELS,
  TRENCH_MAX_LEVEL,
  AIR_ATTACK_VS_GROUND,
  GROUND_DEFENCE_VS_AIR,
  BUILDING_DAMAGE_PER_EFFECTIVE_UNIT,
  FORTRESS,
  PATROL,
  ROSTER_ORDER,
  MAX_UNIT_ROWS,
  STACK_GROUP,
  STACK_GROUP_LABEL,
  HEROES,
  HEROES_LAND_REFUSED,
  HERO_HP_BUFFS,
} from './data.js';

const EPS = 1e-9;

// ---------------------------------------------------------------------------
// Core laws
// ---------------------------------------------------------------------------

/**
 * Stack size factor E(n): the effective unit count a stack of n fights with.
 * MEASURED at n = 10, 15, 20, 29, 30, 45, 50, 57, 113 (see PROVENANCE.E_n).
 * Saturates at 35 effective units, so stacking past 50 does nothing.
 */
export function effectiveUnits(n) {
  const count = Number(n);
  if (!Number.isFinite(count) || count <= 0) return 0;
  if (count <= 20) return count;
  const k = Math.min(count, 50) - 20;
  return 20 + (k * (60 - k)) / 60;
}

/**
 * HP scaling of a stack's OUTPUT. m(f) = 0.05 + 0.95f, f = current/full HP.
 * MEASURED with zero deviation at ten points (see PROVENANCE.m_f).
 * The 0.05 floor is real: a stack at 10% HP deals 14.5% of full damage.
 */
export function hpMultiplier(f) {
  const frac = Number(f);
  if (!Number.isFinite(frac)) return 1;
  return 0.05 + 0.95 * frac;
}

/**
 * Fortress damage reduction from the fortress's CURRENT HP, 0..1.
 * DR = 0.15 * (fortressHP / 50 + 1). MEASURED at levels 1-5 (see
 * PROVENANCE['FORTRESS.dr']).
 *
 * Two deliberate choices at the edges, both unmeasured and both flagged by
 * simulate() when they bind:
 *   - No fortress, or a destroyed one, returns 0. The formula's "+1" would
 *     say 0.15 at zero HP; nobody has measured a destroyed fortress.
 *   - The result is clamped to 1. At level 6 the raw formula returns 1.05,
 *     so it must saturate or the level-5 cap is real; unmeasured either way.
 */
export function fortressDR(fortressHP) {
  const hp = Number(fortressHP);
  if (!Number.isFinite(hp) || hp <= 0) return 0;
  const dr = FORTRESS.drSlopePer50HP * (hp / FORTRESS.hpPerLevel + 1);
  return Math.min(1, Math.max(0, dr));
}

/**
 * Trench multipliers for a level.
 *
 * Returns { pool, output, exact, poolRange, outputRange, poolBracket, level,
 *           requestedLevel, note }.
 *
 * `exact: true` means the level is one of the nine that were actually
 * submitted (0,1,2,3,4,5,10,15,20). For the twelve that were not, the point
 * values are those of the nearest LOWER sampled level and *Range brackets the
 * sampled neighbours — which rests on both curves being non-decreasing, an
 * assumption, not a reading. Neither curve is smooth (output plateaus at x1.40
 * across levels 4 and 5), so interpolating inside a gap is not justified.
 *
 * poolBracket is the measurement interval of the pool multiplier itself, which
 * is a derived quantity even at sampled levels: pool = lost / pct and pct is
 * printed to 3 significant figures.
 */
export function trenchFactors(level) {
  const blank = level === undefined || level === null || level === '';
  const requested = blank ? 0 : Number(level);
  let lvl = Number.isFinite(requested) ? Math.floor(requested) : 0;
  let clean = Number.isFinite(requested) ? Number.isInteger(requested) : true;
  let note = '';
  if (lvl < 0) {
    lvl = 0;
    clean = true;
    note = 'Negative trench level treated as 0.';
  }
  if (lvl > TRENCH_MAX_LEVEL) {
    note = `Trench level ${lvl} is above the form's maximum of ${TRENCH_MAX_LEVEL}; clamped to `
      + `${TRENCH_MAX_LEVEL}, which is the highest level ever submitted.`;
    lvl = TRENCH_MAX_LEVEL;
    clean = false;   // the level asked for was not the level measured
  }

  if (clean && Object.prototype.hasOwnProperty.call(TRENCH_POOL, lvl)) {
    return {
      level: lvl,
      requestedLevel: requested,
      pool: TRENCH_POOL[lvl],
      output: TRENCH_OUTPUT[lvl],
      exact: true,
      poolRange: [TRENCH_POOL[lvl], TRENCH_POOL[lvl]],
      outputRange: [TRENCH_OUTPUT[lvl], TRENCH_OUTPUT[lvl]],
      poolBracket: TRENCH_POOL_BRACKET[lvl],
      note,
    };
  }

  const below = TRENCH_SAMPLED_LEVELS.filter((s) => s <= lvl).pop();
  const above = TRENCH_SAMPLED_LEVELS.find((s) => s > lvl);
  const lo = below === undefined ? 0 : below;
  const hi = above === undefined ? lo : above;
  return {
    level: lvl,
    requestedLevel: requested,
    pool: TRENCH_POOL[lo],
    output: TRENCH_OUTPUT[lo],
    exact: false,
    poolRange: [TRENCH_POOL[lo], TRENCH_POOL[hi]],
    outputRange: [TRENCH_OUTPUT[lo], TRENCH_OUTPUT[hi]],
    poolBracket: TRENCH_POOL_BRACKET[lo],
    note: note || `Trench level ${lvl} was never submitted. Only levels `
      + `${TRENCH_SAMPLED_LEVELS.join(', ')} were sampled. The values shown are `
      + `level ${lo}'s; the true values lie between level ${lo} and level ${hi} `
      + `if both schedules are non-decreasing, which is assumed, not measured.`,
  };
}

// ---------------------------------------------------------------------------
// Coverage
// ---------------------------------------------------------------------------

const LEVEL_ORDER = { measured: 2, estimated: 1, unknown: 0 };

function worst(a, b) {
  return LEVEL_ORDER[a] <= LEVEL_ORDER[b] ? a : b;
}

export function resolveUnit(u) {
  if (!u) return null;
  if (typeof u === 'string') return UNITS[u] || null;
  if (typeof u === 'object' && u.code && UNITS[u.code]) return UNITS[u.code];
  return null;
}

/**
 * How well the record covers one attacker/defender pairing.
 * Returns { level: 'measured'|'estimated'|'unknown', reason }.
 */
/**
 * Is this configuration flown as a patrol, and is that even a legal question?
 *
 * Patrol is only meaningful for an air stack attacking ground: that is the
 * only pairing where both modes were measured. Asking for it anywhere else
 * returns applies:false and the engine falls back to the strike path rather
 * than inventing a second mechanic for a matchup that has neither.
 */
export function patrolMode(mode, atkUnit, defUnit) {
  const a = resolveUnit(atkUnit);
  const d = resolveUnit(defUnit);
  const wanted = mode === 'patrol';
  const eligible = !!(a && d && a.cls === 'air' && d.cls === 'land' && a.code !== 'bal');
  return {
    wanted,
    applies: wanted && eligible,
    eligible,
    ignoredRounds: !wanted && eligible,   // a strike ignores maxRounds entirely
    c: PATROL.attritionCoefficient,
    range: PATROL.attritionRange,
  };
}

/**
 * A side's configured unit rows, normalised.
 *
 * Accepts either the composite form {rows:[{unit,count,hpPct}]} or the old
 * single-unit form {unit,count,hpPct}, which is exactly one row. Duplicate
 * unit types are DROPPED rather than merged, because the server refuses them
 * outright ("The same unit can't be specified twice in same stack") and
 * merging would silently compute a stack the game cannot field.
 */
export function normaliseRows(cfg) {
  const raw = (cfg && Array.isArray(cfg.rows) && cfg.rows.length)
    ? cfg.rows
    : [{ unit: cfg && cfg.unit, count: cfg && cfg.count, hpPct: cfg && cfg.hpPct }];
  const seen = new Set();
  const out = [];
  for (const r of raw) {
    if (out.length >= MAX_UNIT_ROWS) break;
    const u = resolveUnit(r && r.unit);
    if (!u || seen.has(u.code)) continue;
    seen.add(u.code);
    out.push({
      unit: u,
      count: Math.max(0, Math.floor(num(r && r.count, 0))),
      hpPct: Math.min(100, Math.max(0, num(r && r.hpPct, 100))),
    });
  }
  return out;
}

/**
 * Effective units per row: the stack saturates AS A WHOLE and each type draws
 * from what is left, in ROSTER order.
 *
 *     effective_i = E(units through row i) - E(units before row i)
 *
 * Measured to 0.002% across four mixtures. Submission order is irrelevant --
 * the server sorts first, which is why the swapped pair returned an identical
 * figure -- but a type late in the roster order draws from the saturated tail,
 * and that is the whole reason this matters.
 */
/**
 * Which rows the game would actually let share a stack.
 *
 * Measured: classes never mix, and the Airplane Convoy stacks with nothing.
 * A stack the server refuses is not a battle with an uncertain answer -- it
 * is not a battle at all -- so the engine reports the conflict rather than
 * computing a number for an army that cannot be fielded.
 */
/**
 * A hero's stack multiplier at a given level.
 *
 * The measured points are stored verbatim and a level between them is
 * INTERPOLATED, because neither buffing hero's curve is a clean line or a
 * clean step: joffre_home is exactly 1.10 + 0.02*level from level 5 up, but
 * levels 1-4 read 1.10 / 1.15 / - / 1.16 and fit nothing. Fitting a formula
 * through that would be inventing nineteen values from eight.
 */
export function heroBuff(code, level, unitCode) {
  const h = HEROES[code];
  if (!h) return { m: null, exact: false, note: 'unknown hero' };
  const table = h.buffs || {};
  const curve = unitCode ? table[unitCode] : null;
  if (!curve) {
    const targets = Object.keys(table);
    return { m: 1.0, exact: true,
             note: targets.length
               ? `${h.label} buffs ${targets.join(' and ')}, not this unit type `
                 + '(measured: its excess over its own attack was zero on the '
                 + 'other seven land types)'
               : `${h.label} is a pure combat unit — it raised a nine-type `
                 + 'stack by exactly its own attack value and nothing more.' };
  }
  const lv = Math.max(1, Math.min(h.maxLevel || 20, Math.round(num(level, 1))));
  const pts = Object.keys(curve).map(Number).sort((a, b) => a - b);
  if (curve[lv] !== undefined) {
    return { m: curve[lv], exact: true, note: `measured directly at level ${lv}` };
  }
  // A single measured level is not a curve. The non-infantry buffs were found
  // by a screen run entirely at level 10, so every other level is an
  // assumption -- and joffre_home's infantry curve, the only one measured
  // across levels, is neither a line nor a step, so there is no shape to
  // borrow with a straight face.
  if (pts.length === 1) {
    return { m: curve[pts[0]], exact: false,
             note: `only level ${pts[0]} was ever measured for this unit type `
               + `(x${curve[pts[0]]}); level ${lv} assumes the same figure, and `
               + `the one hero whose curve WAS measured across levels moves `
               + `from x1.10 to x1.40, so this could be well off` };
  }
  const below = pts.filter((x) => x < lv).pop();
  const above = pts.find((x) => x > lv);
  if (below === undefined || above === undefined) {
    const near = below === undefined ? above : below;
    return { m: curve[near], exact: false,
             note: `level ${lv} is outside the measured range (${pts[0]}-`
               + `${pts[pts.length - 1]}); using level ${near}` };
  }
  const t = (lv - below) / (above - below);
  return { m: curve[below] + t * (curve[above] - curve[below]), exact: false,
           note: `level ${lv} was never submitted; interpolated between the `
             + `measured levels ${below} (x${curve[below]}) and ${above} `
             + `(x${curve[above]})` };
}

export function stackGroupsOf(rows) {
  const groups = new Set();
  for (const r of rows || []) {
    const code = r && r.unit && (r.unit.code || r.unit);
    if (code) groups.add(STACK_GROUP[code] || 'unknown');
  }
  return [...groups];
}

export function effectiveByRow(rows, column) {
  const col = column === 'atk' ? 'atk' : 'def';
  const list = (rows || []).map((r, i) => ({ r, i }));
  // STRONGEST FIRST, by the column the side is actually using. Measured on a
  // ladder from one to nine unit types: fits every rung to 0.002%, and
  // predicted three held-out stacks it was not fitted to, to the same figure.
  //
  // This engine shipped ROSTER order until that ladder was run. The two are
  // the same function whenever the roster happens to list a stack's types
  // strongest-first, which is exactly what every mixture measured before it
  // did -- all of them were infantry + artillery, and infantry both precedes
  // artillery in the roster and out-damages it. On a stack of light artillery
  // and heavy tanks the two differ by 2.3x.
  const rank = (r) => {
    const u = r && r.unit;
    const v = u && typeof u[col] === 'number' ? u[col] : null;
    return v === null ? -Infinity : v;
  };
  list.sort((a, b) => rank(b.r) - rank(a.r) || a.i - b.i);
  const eff = new Array((rows || []).length).fill(0);
  let seen = 0;
  for (const { r, i } of list) {
    const c = Math.max(0, num(r && r.count, 0));
    eff[i] = effectiveUnits(seen + c) - effectiveUnits(seen);
    seen += c;
  }
  return (rows || []).map((r, i) => ({ ...r, effective: eff[i] }));
}

/**
 * How incoming damage is split across a stack's rows: in proportion to
 * (attack value x unit count) -- each row's raw offensive weight, ignoring the
 * saturation that output obeys.
 *
 * Exact on all four measured mixtures, including the asymmetric ones where
 * allocation by pool is off by 10.7 HP and by attack-value-alone by 26.6 in
 * the wrong direction. It uses the unit's ATTACK stat even for a defending
 * stack, which is not obvious and is what the readings say.
 */
export function allocationWeights(rows) {
  return (rows || []).map((r) => {
    const atk = r && r.unit && typeof r.unit.atk === 'number' ? r.unit.atk : 0;
    return Math.max(0, atk * Math.max(0, num(r && r.count, 0)));
  });
}

/**
 * Coverage for two COMPOSITE stacks: the worst cell of the cross-product.
 *
 * A stack of 10 infantry + 40 artillery attacking 30 infantry + 10 cavalry is
 * four pairings, and only one of them is the measured diagonal. Judging on the
 * first row of each side reported "measured" on the strength of
 * infantry-vs-infantry while cavalry-vs-artillery -- never submitted once --
 * went unmentioned. That is precisely the confident-wrong-answer failure this
 * project exists to avoid, so the verdict is the WORST pairing present and it
 * names which one it is.
 */
export function coverageOfStacks(atkRows, defRows) {
  const a = (atkRows || []).filter((r) => r.count > 0);
  const d = (defRows || []).filter((r) => r.count > 0);
  if (!a.length || !d.length) {
    return { level: 'unknown', reason: 'A side has no units.', pairs: [] };
  }
  const rank = { measured: 0, estimated: 1, unknown: 2 };
  const pairs = [];
  for (const ar of a) {
    for (const dr of d) {
      const c = coverageOf(ar.unit, dr.unit);
      pairs.push({ atk: ar.unit, def: dr.unit, ...c });
    }
  }
  pairs.sort((x, y) => rank[y.level] - rank[x.level]);
  const worstPair = pairs[0];
  const nPairs = pairs.length;
  if (nPairs === 1) return { ...worstPair, pairs };
  const bad = pairs.filter((p) => p.level !== 'measured');
  const lead = bad.length
    ? `${bad.length} of ${nPairs} unit pairings in this battle are not measured. `
      + `The worst is ${worstPair.atk.label} vs ${worstPair.def.label}: `
    : `All ${nPairs} unit pairings in this battle are measured. `;
  return {
    level: worstPair.level,
    reason: lead + worstPair.reason,
    pairs,
  };
}

export function coverageOf(atkUnit, defUnit) {
  const a = resolveUnit(atkUnit);
  const d = resolveUnit(defUnit);

  if (!a || !d) {
    return { level: 'unknown', reason: 'Unrecognised unit code — nothing in the record applies.' };
  }
  if (a.code === 'bal' || d.code === 'bal') {
    return {
      level: 'unknown',
      reason: 'The Balloon has nothing measured at all — no max HP, no attack, no defence. '
        + 'Sending it in air terrain aborts the whole request server-side, so its fourteen rows '
        + 'in results.jsonl are all empty.',
    };
  }
  if (a.cls === 'air' && d.cls === 'land') {
    return {
      level: 'measured',
      reason: 'Air attacking ground is the one cross-class pairing anyone has measured: 30 cells, '
        + 'three fliers against all ten ground units. The attacker\'s stat is flat across every '
        + 'target and each ground defence value is confirmed by three independent attackers.',
    };
  }
  if (a.code === d.code) {
    return {
      level: 'measured',
      reason: `${a.label} against its own kind is the measured diagonal — a 10 v 10 duel flown four `
        + 'times with byte-identical readings.',
    };
  }
  if (a.cls === d.cls) {
    return {
      level: 'estimated',
      reason: `${a.label} vs ${d.label} is off-diagonal within ${a.cls}: this exact pairing has never `
        + 'been submitted. Each side is given its own same-class stat as a stand-in. Attack is KNOWN '
        + 'to vary by target class (the Bomber is 3.0 against air and 30.0 against ground), so it may '
        + 'vary by target unit too — this number could be wrong by any factor.',
    };
  }
  if (a.cls === 'land' && d.cls === 'air') {
    return {
      level: 'unknown',
      reason: 'A ground stack ATTACKING air has never been measured. The record contains ground '
        + 'DEFENCE against air, which is the other role and does not transfer. No number is offered.',
    };
  }
  return {
    level: 'unknown',
    reason: `${a.cls} attacking ${d.cls} has never been submitted. No coefficient exists in either `
      + 'direction, so the engine withholds the numbers rather than inventing them.',
  };
}

/**
 * The attacking side's per-effective-unit output stat against this defender.
 * { value, level, source } — value null means "no reading exists".
 */
export function attackCoefficient(atkUnit, defUnit) {
  const a = resolveUnit(atkUnit);
  const d = resolveUnit(defUnit);
  if (!a || !d) return { value: null, level: 'unknown', source: 'unrecognised unit' };
  if (a.cls === 'air' && d.cls === 'land') {
    const v = AIR_ATTACK_VS_GROUND[a.code];
    if (v === undefined) {
      return { value: null, level: 'unknown', source: `no air-to-ground reading for ${a.code}` };
    }
    return { value: v, level: 'measured', source: 'AIR_ATTACK_VS_GROUND (30 cells, flat across all ten ground targets)' };
  }
  if (a.code === d.code) {
    if (a.atk === null) return { value: null, level: 'unknown', source: `${a.code} has no measured attack` };
    return { value: a.atk, level: 'measured', source: 'UNITS.diagonal (same-class 10v10 duel)' };
  }
  if (a.cls === d.cls) {
    if (a.atk === null) return { value: null, level: 'unknown', source: `${a.code} has no measured attack` };
    return { value: a.atk, level: 'estimated', source: `${a.label}'s same-class diagonal stat used as a stand-in for a target that was never tested` };
  }
  return { value: null, level: 'unknown', source: `no reading for ${a.cls} attacking ${d.cls}` };
}

/**
 * The defending side's per-effective-unit output stat against this attacker.
 */
export function defenceCoefficient(defUnit, atkUnit) {
  const d = resolveUnit(defUnit);
  const a = resolveUnit(atkUnit);
  if (!a || !d) return { value: null, level: 'unknown', source: 'unrecognised unit' };
  if (a.cls === 'air' && d.cls === 'land') {
    const v = GROUND_DEFENCE_VS_AIR[d.code];
    if (v === undefined) {
      return { value: null, level: 'unknown', source: `no ground-defence reading for ${d.code}` };
    }
    return { value: v, level: 'measured', source: 'GROUND_DEFENCE_VS_AIR (each value confirmed by three independent attackers)' };
  }
  if (a.code === d.code) {
    if (d.def === null) return { value: null, level: 'unknown', source: `${d.code} has no measured defence` };
    return { value: d.def, level: 'measured', source: 'UNITS.diagonal (same-class 10v10 duel)' };
  }
  if (a.cls === d.cls) {
    if (d.def === null) return { value: null, level: 'unknown', source: `${d.code} has no measured defence` };
    return { value: d.def, level: 'estimated', source: `${d.label}'s same-class diagonal stat used as a stand-in for an attacker that was never tested` };
  }
  return { value: null, level: 'unknown', source: `no reading for ${d.cls} defending against ${a.cls}` };
}

// ---------------------------------------------------------------------------
// simulate()
// ---------------------------------------------------------------------------

function num(v, fallback) {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}

function makeSide(cfg, role, derivation, caveats) {
  let side_groupConflict = null;
  let side_hero = null;
  const label = role === 'attacker' ? 'Attacker' : 'Defender';
  const tf = trenchFactors(cfg && cfg.trench);

  // A stack is a MIXTURE of distinct unit types. The single-unit form is one
  // row; everything below works the same either way, and for one row the
  // per-row arithmetic reduces exactly to what it was before.
  const rawRows = (cfg && Array.isArray(cfg.rows) && cfg.rows.length)
    ? cfg.rows : null;
  const rows = effectiveByRow(normaliseRows(cfg),
                              role === 'attacker' ? 'atk' : 'def');
  const dropped = rawRows
    ? rawRows.length - normaliseRows(cfg).length : 0;
  if (dropped > 0) {
    caveats.push(`${label}: ${dropped} unit row(s) dropped. A stack cannot hold `
      + 'the same unit type twice — the server refuses it outright — and an '
      + 'unrecognised unit has no constants.');
  }

  for (const r of rows) {
    r.perUnitMaxHP = (r.unit && r.unit.maxHP !== null)
      ? r.unit.maxHP * tf.pool : null;
    r.poolFull = r.perUnitMaxHP === null ? null : r.count * r.perUnitMaxHP;
    r.pool = r.poolFull === null ? null : r.poolFull * (r.hpPct / 100);
    r.hpLost = 0;
    r.deaths = 0;
    // null, not 0. A path that cannot decompose the stack's output per row --
    // the air and patrol laws work on whole-stack survivors -- must say it has
    // no figure. Zero is a claim, and it was a false one.
    r.damageDealt = null;
  }

  // A stack the game refuses to field. Flagged on the side that carries it,
  // and escalated to `unknown` below rather than quietly computed.
  const groups = stackGroupsOf(rows);
  side_groupConflict = null;
  if (groups.length > 1) {
    const names = groups.map((g) => STACK_GROUP_LABEL[g] || g).join(' and ');
    side_groupConflict = `${label}: ${names} units cannot share a stack. The `
      + 'server refuses this outright ("Can\'t have ground and air units in same '
      + 'stack", "Convoys don\'t stack with land units"), so this is not an '
      + 'uncertain battle — it is not a battle the game will run.';
    caveats.push(side_groupConflict);
  }

  // THE HERO. One per stack (addHero refuses a second). It fights as a single
  // unit at its own attack value, and multiplies what the rest of the stack
  // deals. Where it sits is measured per hero and changes both effective
  // counts, because the stack saturates cumulatively in roster order.
  const heroCfg = cfg && cfg.hero;
  let hero = null;
  if (heroCfg && heroCfg.code) {
    const known = HEROES[heroCfg.code];
    const refused = HEROES_LAND_REFUSED[heroCfg.code];
    if (known) {
      const lvl = Math.max(1, Math.min(known.maxLevel,
        Math.round(num(heroCfg.level, 1))));
      if (num(heroCfg.level, 1) > known.maxLevel) {
        caveats.push(`${label}: ${known.label} caps at level ${known.maxLevel} — `
          + `the server states so outright and refuses anything higher, even `
          + `though the form offers 1-20 for every hero. Clamped.`);
      }
      // A hero may also raise the max HP of one specific unit type. The engine
      // has no term for that, so a battle containing such a pair is WRONG in
      // the pool rather than merely uncertain, and must say so.
      const hpBuffs = HERO_HP_BUFFS[heroCfg.code] || {};
      const hit = rows.filter((r) => hpBuffs[r.unit.code]);
      if (hit.length) {
        caveats.push(`${label}: ${known.label} also raises the max HP of `
          + hit.map((r) => `${r.unit.label} (x${hpBuffs[r.unit.code]})`).join(' and ')
          + '. That is a measured effect on the HP POOL, and this engine has no '
          + 'term for it — the pools below are too LOW for those rows, and the '
          + 'deaths with them.');
      }
      // A hero's output buff is PER UNIT TYPE, not per stack. joffre_home
      // raises infantry AND armoured cars by 1.30 and leaves the other seven
      // land types alone; alvin raises only stormtroopers, by 1.40. Applying
      // one figure to the whole stack over-counts every row it does not cover.
      const buffs = {};
      let anyInexact = null;
      for (const r of rows) {
        const b = heroBuff(heroCfg.code, lvl, r.unit.code);
        buffs[r.unit.code] = b;
        if (b.m !== 1 && !b.exact) anyInexact = b;
      }
      const hitOut = rows.filter((r) => buffs[r.unit.code].m !== 1);
      const infBuff = heroBuff(heroCfg.code, lvl, 'inf');
      hero = { code: heroCfg.code, def: known, level: lvl, atk: known.atk,
               buffs, m: infBuff.m, exact: infBuff.exact, note: infBuff.note,
               buffedRows: hitOut.length };
      hero.hpBuffHits = hit.length;
      if (hitOut.length) {
        derivation.push({
          label: `${label} hero output buff`,
          formula: hitOut.map((r) => `${r.unit.label} x`
            + `${round4(buffs[r.unit.code].m)}`).join(', ')
            + ` — ${known.label} at level ${lvl}; every other row is unbuffed`,
          value: buffs[hitOut[0].unit.code].m,
        });
      }
      if (anyInexact) {
        hero.interpolated = true;
        caveats.push(`${label}: ${known.label} — ${anyInexact.note}.`);
      }
    } else if (refused) {
      hero = { code: heroCfg.code, refused };
      caveats.push(`${label}: ${refused.label} has nothing measured against a `
        + `land stack — ${refused.why} No hero effect is applied.`);
    } else {
      caveats.push(`${label}: unrecognised hero "${heroCfg.code}" ignored.`);
    }
  }
  side_hero = hero && hero.def ? hero : null;

  const primary = rows.length ? rows[0].unit : resolveUnit(cfg && cfg.unit);
  const n = rows.reduce((t, r) => t + r.count, 0);
  const anyPoolUnknown = rows.some((r) => r.pool === null);
  const poolFull = (!rows.length || anyPoolUnknown)
    ? null : rows.reduce((t, r) => t + r.poolFull, 0);
  const poolNow = (!rows.length || anyPoolUnknown)
    ? null : rows.reduce((t, r) => t + r.pool, 0);
  // The stack-level HP percentage, for the derivation and for m(f) where a
  // stack is single-type. With mixed percentages this is the pool-weighted
  // figure, which is what m(f) would see if it reads the whole stack.
  const hpPct = poolFull ? (poolNow / poolFull) * 100 : 100;
  const unit = primary;

  const side = {
    role, label, unit, rows, n0: n, n, hpPct, tf,
    groupConflict: side_groupConflict,
    hero: side_hero,
    perUnitMaxHP: null, poolFull: 0, pool: 0,
    hpLost: 0, deaths: 0, damageDealt: 0, outputRaw: 0, wiped: false,
    buildings: [],
    damageToBuildings: null,
  };

  if (rows.length && !anyPoolUnknown) {
    side.perUnitMaxHP = rows[0].perUnitMaxHP;
    side.poolFull = poolFull;
    side.pool = poolNow;
    for (const r of rows) {
      derivation.push({
        label: `${label} row: ${r.count} x ${r.unit.label}`,
        formula: `${r.count} units x ${round4(r.perUnitMaxHP)} HP`
          + `${r.hpPct !== 100 ? ` x ${r.hpPct}%` : ''} = ${round4(r.pool)} pool`
          + `; effective units ${round4(r.effective)}`
          + (Math.abs(r.effective - r.count) > 0.01
            ? ` (of ${r.count} — the stack has saturated)` : ''),
        value: r.pool,
      });
    }
    if (rows.length > 1) {
      derivation.push({
        label: `${label} stack saturation`,
        formula: `${n} units total. Each type draws from E(${n})=`
          + `${round4(effectiveUnits(n))} STRONGEST FIRST, by its own `
          + `${role === 'attacker' ? 'attack' : 'defence'} value, so the `
          + `weakest type in the stack gets what is left: `
          + `${rows.map((r) => `${r.unit.code} ${round4(r.effective)}`).join(', ')}`
          + ' (measured on a nine-type ladder, 0.002%, and held out on three '
          + 'stacks it was not fitted to)',
        value: effectiveUnits(n),
      });
    }
    derivation.push({
      label: `${label} HP pool`,
      formula: rows.length === 1
        ? `${n} units x ${round4(side.perUnitMaxHP)} HP x ${round4(hpPct)}% = ${round4(side.pool)}`
        : `sum of ${rows.length} rows = ${round4(side.pool)}`,
      value: side.pool,
    });
  } else if (unit && unit.maxHP !== null) {
    side.pool = null;
    side.poolFull = null;
    derivation.push({
      label: `${label} HP pool`,
      formula: 'A unit row has no measured max HP — no pool can be computed.',
      value: null,
    });
  } else {
    derivation.push({
      label: `${label} HP pool`,
      formula: unit
        ? `${unit.label} has no measured max HP — no pool can be computed.`
        : 'Unrecognised unit — no pool can be computed.',
      value: null,
    });
    side.pool = null;
    side.poolFull = null;
  }

  // Buildings
  const list = Array.isArray(cfg && cfg.buildings) ? cfg.buildings : [];
  for (const b of list) {
    const def = b && BUILDINGS[b.code];
    if (!def) {
      caveats.push(`${label}: unrecognised building "${b && b.code}" ignored.`);
      continue;
    }
    let lvl = Math.max(1, Math.floor(num(b.level, 1)));
    if (def.maxLevel !== null && lvl > def.maxLevel) {
      caveats.push(`${label}: ${def.label} level ${lvl} exceeds the server's stated cap of `
        + `${def.maxLevel} (the server rejects it outright rather than clamping); clamped to ${def.maxLevel}.`);
      lvl = def.maxLevel;
    }
    if (def.maxLevel === null) {
      caveats.push(`${label}: the server's level cap for ${def.label} was never established — `
        + 'the sweep asked for 3, was not rejected, and never probed higher.');
    }
    const bHpPct = Math.min(100, Math.max(0, num(b.hpPct, 100)));
    let full = null;
    if (def.poolAtLevel && def.poolAtLevel[lvl] !== undefined) {
      full = def.poolAtLevel[lvl];
    } else if (def.hpPerLevel !== null) {
      full = def.hpPerLevel * lvl;
      caveats.push(`${label}: ${def.label} HP at level ${lvl} is extrapolated from a single `
        + 'observation at another level, not measured.');
    } else {
      caveats.push(`${label}: ${def.label} HP at level ${lvl} is unmeasured — its HP is not `
        + 'uniform per level (35 total at L3 with 20 in the top level), so it cannot be extrapolated.');
    }
    side.buildings.push({
      code: def.code, label: def.label, level: lvl,
      hpFull: full, hp: full === null ? null : full * (bHpPct / 100),
      hpLost: 0, destroyed: false, mitigates: def.mitigates,
    });
  }
  return side;
}

function round4(x) {
  return x === null || x === undefined ? x : Math.round(x * 1e6) / 1e6;
}

function fortressOf(side) {
  return side.buildings.find((b) => b.mitigates && b.hp !== null && b.hp > 0) || null;
}

function stackFraction(side) {
  if (side.pool === null || side.n <= 0 || !side.perUnitMaxHP) return 0;
  return side.pool / (side.n * side.perUnitMaxHP);
}

/**
 * One round of combat, or a whole battle if config.rounds > 1 (which is
 * unmeasured — every reading in the record used maxRounds = 1).
 *
 * Returns a Result. Never throws.
 */
export function simulate(config) {
  const derivation = [];
  const caveats = [];

  try {
    return runSimulation(config || {}, derivation, caveats);
  } catch (err) {
    // A defect here must not become a plausible wrong answer.
    derivation.push({
      label: 'Internal error',
      formula: `The engine failed while computing this configuration: ${err && err.message}`,
      value: null,
    });
    return {
      attacker: emptySideResult(),
      defender: emptySideResult(),
      coverage: {
        level: 'unknown',
        reason: 'The engine failed on this configuration, so no number below is trustworthy.',
        caveats: caveats.concat([`Internal error: ${err && err.message}`]),
      },
      derivation,
    };
  }
}

function emptySideResult() {
  return {
    pool: null, hpLost: null, pctLost: null, deaths: null, unitsLeft: null,
    damageDealt: null, wiped: false, outputRaw: null, damageToBuildings: null,
    buildings: [],
  };
}

function runSimulation(config, derivation, caveats) {
  const atk = makeSide(config.attacker, 'attacker', derivation, caveats);
  const def = makeSide(config.defender, 'defender', derivation, caveats);

  const matchup = coverageOfStacks(atk.rows, def.rows);
  const conflicts = [atk.groupConflict, def.groupConflict].filter(Boolean);
  let level = matchup.level;
  const reasons = [matchup.reason];

  // An interpolated hero level is an ESTIMATE, and the banner is the one place
  // a reader actually looks. A caveat bullet under a green "Measured matchup"
  // headline is not enough — the app shipped exactly that for a moment.
  for (const sd of [atk, def]) {
    if (sd.hero && sd.hero.hpBuffHits) {
      level = worst(level, 'estimated');
      reasons.push(`The ${sd.role}'s hero raises the max HP of a unit type in `
        + 'its own stack, and this engine does not model HP buffs — those pools '
        + 'are understated.');
    }
    if (sd.hero && sd.hero.interpolated) {
      level = worst(level, 'estimated');
      reasons.push(`The ${sd.role}'s hero sits at a level that was never `
        + 'submitted, so its stack multiplier is interpolated between measured '
        + 'levels rather than read off one.');
    }
  }

  // ---- mode: direct strike or patrol ---------------------------------------
  const patrol = patrolMode(config.mode || (config.attacker && config.attacker.mode),
                            atk.unit, def.unit);
  if (patrol.wanted && !patrol.eligible) {
    caveats.push('Patrol was requested but only ever measured for an AIR stack attacking GROUND. '
      + 'This pairing is computed as a direct engagement instead; patrol semantics elsewhere are '
      + 'unmeasured.');
  }

  // ---- rounds --------------------------------------------------------------
  let rounds = num(config.rounds, 1);
  if (!Number.isFinite(rounds) || rounds <= 0) rounds = 1;

  if (patrol.applies) {
    // MEASURED: patrol damage is proportional to maxRounds. A ladder of
    // 0.25/0.5/0.75/1 gives a flat 30.13-30.33 per unit per round, so
    // fractional rounds are real here and are the finest instrument available.
    if (rounds > 4) {
      level = worst(level, 'estimated');
      caveats.push(`Patrol was measured only up to maxRounds = 1. Scaling to ${rounds} assumes the `
        + 'proportionality holds indefinitely, which nobody has checked.');
    }
    derivation.push({
      label: 'Mode: PATROL',
      formula: `Damage is proportional to maxRounds (measured: rate flat across `
        + `0.25/0.5/0.75/1). Scaling by ${round4(rounds)}.`,
      value: rounds,
    });
  } else if (patrol.ignoredRounds) {
    // MEASURED, and corrected: a direct strike is ATOMIC, not roundless. It
    // cannot be subdivided, so 0.25/0.5/0.75 all deliver exactly one strike --
    // but WHOLE rounds repeat normally (295.01 / 585.23 / 871.68 at 1, 2, 3).
    //
    // The earlier reading, "maxRounds is ignored in air", came from testing
    // only 0.25 to 1, where the two behaviours are indistinguishable. dxcalc's
    // own help page said otherwise and was right.
    if (!Number.isInteger(rounds)) {
      const up = Math.max(1, Math.ceil(rounds));
      caveats.push(`A direct air strike cannot be subdivided: 0.25, 0.5 and 0.75 all `
        + `deliver one whole strike (measured, byte-identical). Computing `
        + `${up} round(s). Patrol DOES subdivide — switch mode if you want a partial tick.`);
      rounds = up;
    }
    derivation.push({
      label: 'Mode: DIRECT STRIKE',
      formula: `An air strike is atomic — fractional rounds deliver one whole strike `
        + `(measured) — but whole rounds repeat. Computing ${round4(rounds)}.`,
      value: rounds,
    });
    if (rounds > 1) {
      level = worst(level, 'estimated');
      reasons.push('Multi-round: the engine iterates rounds, and round-to-round '
        + 'carry-over was never measured directly — only the totals were.');
    }
  } else {
    if (!Number.isInteger(rounds)) {
      caveats.push(`Fractional rounds (${rounds}) are measured only for patrol, which does not `
        + `apply here. Computing ${Math.max(1, Math.floor(rounds))} whole round(s) instead.`);
      rounds = Math.max(1, Math.floor(rounds));
    }
    if (rounds !== 1) {
      level = worst(level, 'estimated');
      reasons.push('Multi-round: EVERY measurement in the record used maxRounds = 1, so '
        + 'round-to-round carry-over is an extrapolation of the engine, not a reading.');
      caveats.push(`${rounds} rounds requested. Round-to-round carry-over, whether m(f) re-evaluates `
        + 'each round, and whether fortress DR decays between rounds are all unmeasured.');
    }
  }

  if (patrol.applies) {
    // The base stat is the same in both modes and that IS measured. What is
    // not pinned is the attrition coefficient, so the whole result drops to
    // estimated no matter how clean the matchup itself is.
    level = worst(level, 'estimated');
    reasons.push('Flown as a PATROL. The attack stat is unchanged from a direct strike (measured: '
      + 'every attacker\'s value comes back through patrol), but patrol charges only part of the '
      + 'attacker\'s own losses against its output, and that fraction is NOT pinned — nine cells '
      + `give ${patrol.range[0]}-${patrol.range[1]} and the scatter does not track the loss `
      + 'fraction. This result uses 3/8 as a working value.');
    caveats.push(`Patrol attrition coefficient is a band, not a number: ${patrol.range[0]}-`
      + `${patrol.range[1]} over ${PATROL.cellsMeasured} cells. The delivery is probably discrete `
      + '(ticks, or whole units dying at tick boundaries), so treat the damage figure as a central '
      + 'estimate with a few percent either side, not a prediction.');
  }

  // ---- coefficients --------------------------------------------------------
  const atkCoef = attackCoefficient(atk.unit, def.unit);
  const defCoef = defenceCoefficient(def.unit, atk.unit);
  const attenuated = !!(atk.unit && def.unit && atk.unit.cls === 'air' && def.unit.cls === 'land');

  derivation.push({
    label: 'Attacker stat (per effective unit)',
    formula: atkCoef.value === null
      ? `No reading exists: ${atkCoef.source}.`
      : `${atkCoef.value} — ${atkCoef.source} [${atkCoef.level}]`,
    value: atkCoef.value,
  });
  derivation.push({
    label: 'Defender stat (per effective unit)',
    formula: defCoef.value === null
      ? `No reading exists: ${defCoef.source}.`
      : `${defCoef.value} — ${defCoef.source} [${defCoef.level}]`,
    value: defCoef.value,
  });

  if (conflicts.length) {
    level = 'unknown';
    reasons.length = 0;
    reasons.push(conflicts.join(' '));
    derivation.push({
      label: 'Result withheld',
      formula: 'This stack cannot exist. The game refuses to field it, so there '
        + 'is no battle to compute and no number is offered.',
      value: null,
    });
    return {
      attacker: sideResult(atk, true),
      defender: sideResult(def, true),
      coverage: { level, reason: reasons.join(' '), caveats, pairs: matchup.pairs || [] },
      derivation,
    };
  }

  if (atkCoef.value === null || defCoef.value === null
      || atk.pool === null || def.pool === null) {
    level = 'unknown';
    derivation.push({
      label: 'Result withheld',
      formula: 'At least one coefficient for this pairing has never been measured. The engine '
        + 'refuses to substitute a number rather than present an invention as a prediction.',
      value: null,
    });
    return {
      attacker: sideResult(atk, true),
      defender: sideResult(def, true),
      coverage: { level, reason: reasons.join(' '), caveats, pairs: matchup.pairs || [] },
      derivation,
    };
  }

  // ---- standing caveats that do not change the numbers ---------------------
  if (!atk.tf.exact) {
    level = worst(level, 'estimated');
    caveats.push(`Attacker: ${atk.tf.note}`);
  }
  if (!def.tf.exact) {
    level = worst(level, 'estimated');
    caveats.push(`Defender: ${def.tf.note}`);
  }
  if (atk.tf.pool !== 1 || atk.tf.output !== 1 || def.tf.pool !== 1 || def.tf.output !== 1) {
    if ((atk.unit && atk.unit.code !== 'inf') || (def.unit && def.unit.code !== 'inf')) {
      caveats.push('Trench multipliers were measured with infantry only. That they are '
        + 'unit-independent and purely multiplicative is assumed.');
    }
    if (def.tf.output !== 1 && def.n > 20) {
      level = worst(level, 'estimated');
      caveats.push('The defender\'s trench output bonus was only ever measured at 10 units, where '
        + 'E(n) = n. Whether it multiplies the stat or the effective unit count is undetermined, '
        + 'and above 20 units the two readings diverge.');
    }
  }
  if (atk.tf.pool !== 1) {
    caveats.push('The trench HP bonus is applied to the attacker: one row measured it (attacker '
      + 'trench 20 gave pool x1.35 and turned 2 deaths into 1). The trench OUTPUT bonus is not '
      + 'applied while attacking — the same row left the defender\'s loss at exactly the control value.');
  }
  if (atk.buildings.length) {
    caveats.push('Buildings on the ATTACKING side are inert in this model. Nobody has ever '
      + 'submitted one, so whether they mitigate or take damage is unknown.');
  }
  if (def.buildings.length > 1) {
    caveats.push('Every buildings measurement used exactly one building. Which building absorbs '
      + 'the damage when there are several is unmeasured; this engine applies it to the first.');
  }
  if (atk.hpPct < 100 && atk.unit.code !== 'inf') {
    caveats.push('m(f) was swept only on an ATTACKING INFANTRY stack. That it applies identically '
      + 'to other unit types is assumed.');
  }
  if (def.hpPct < 100) {
    caveats.push('m(f) was swept only on the ATTACKER. That a damaged DEFENDER\'s output scales the '
      + 'same way is assumed, not measured.');
  }
  const fort = fortressOf(def);
  if (fort) {
    if (atk.unit.cls !== 'land') {
      level = worst(level, 'estimated');
      caveats.push('Fortress mitigation was measured only against a land (infantry) attacker. '
        + 'Whether it applies to an air or naval attacker is unmeasured.');
    }
    if (fort.level > FORTRESS.maxMeasuredLevel) {
      level = worst(level, 'estimated');
      caveats.push(`Fortress DR above level ${FORTRESS.maxMeasuredLevel} is unmeasured; at level 6 `
        + 'the formula returns 1.05, so it must saturate or the cap is real.');
    }
    if (def.tf.pool !== 1 || def.tf.output !== 1) {
      caveats.push('Fortress and trench have never been measured together on the same side.');
    }
  }

  const bdRate = BUILDING_DAMAGE_PER_EFFECTIVE_UNIT[atk.unit.code];
  if (def.buildings.length && bdRate === undefined) {
    caveats.push(`Damage to buildings has only ever been measured for infantry (0.3 per effective `
      + `unit). There is no reading for ${atk.unit.label}, and nothing in the model predicts it, so `
      + 'building damage is withheld.');
  }

  // ---- rounds --------------------------------------------------------------
  // Patrol treats maxRounds as a DURATION and scales one pass by it (measured:
  // the per-round rate is flat across a 0.25/0.5/0.75/1 ladder). Everything
  // else iterates whole rounds. Looping a fractional count would run zero
  // times and silently return no damage at all.
  const loopRounds = patrol.applies ? 1 : rounds;
  const patrolScale = patrol.applies ? rounds : 1;
  for (let r = 1; r <= loopRounds; r += 1) {
    const tag = loopRounds > 1 ? `R${r} ` : '';
    if (atk.n <= 0 || def.n <= 0 || atk.pool <= EPS || def.pool <= EPS) {
      derivation.push({
        label: `${tag}round skipped`,
        formula: 'One side has no surviving HP; the battle is over.',
        value: null,
      });
      break;
    }

    const atkE = effectiveUnits(atk.n);
    const defE = effectiveUnits(def.n);
    const atkF = stackFraction(atk);
    const defF = stackFraction(def);

    derivation.push({
      label: `${tag}Attacker effective units E(${atk.n})`,
      formula: atk.n <= 20 ? `n <= 20, so E = n = ${atk.n}`
        : `20 + k(60-k)/60 with k = min(${atk.n},50)-20 = ${round4(atkE)}`,
      value: atkE,
    });
    derivation.push({
      label: `${tag}Defender effective units E(${def.n})`,
      formula: def.n <= 20 ? `n <= 20, so E = n = ${def.n}`
        : `20 + k(60-k)/60 with k = min(${def.n},50)-20 = ${round4(defE)}`,
      value: defE,
    });

    // 1. Defender's output — always from the PRE-round state (measured: a
    //    ground defender is not attenuated even losing 26% of its pool).
    const defParts = stackOutput(def, (u) => defenceCoefficient(u, atk.unit).value,
                                 def.tf.output * patrolScale);
    const defOutput = defParts.total === null ? 0 : defParts.total;
    if (def.rows.length > 1 || def.hero) {
      for (const pt of defParts.parts) {
        if (pt.hero) {
          derivation.push({
            label: `${tag}Defender hero: ${def.hero.def.label}`,
            formula: `${pt.coef} attack x ${round4(pt.mul)} effective = `
              + `${round4(pt.out)} — fights as one unit, sitting `
              + `${def.hero.def.sits} in the stack`
              + (def.hero.buffedRows
                ? `; it also multiplies ${def.hero.buffedRows} row(s) of the `
                  + 'stack — see the output buff line above'
                : '; it buffs no unit type in this stack (measured)'),
            value: pt.out,
          });
          continue;
        }
        derivation.push({
          label: `${tag}Defender output: ${pt.row.unit.label}`,
          formula: `${pt.coef} x ${round4(pt.row.effective)} effective x `
            + `m(${round4(pt.row.hpPct / 100)})=${round4(pt.mul)}`
            + (pt.heroM && pt.heroM !== 1 ? ` x hero ${round4(pt.heroM)}` : '')
            + ` = ${round4(pt.out)}`,
          value: pt.out,
        });
      }
    }
    derivation.push({
      label: `${tag}Defender output`,
      formula: (def.rows.length > 1 || def.hero)
        ? `sum of ${def.rows.length + (def.hero ? 1 : 0)} rows`
          + `${def.tf.output !== 1 ? ` x trench ${def.tf.output}` : ''}`
          + `${patrolScale !== 1 ? ` x ${round4(patrolScale)} rounds` : ''} = ${round4(defOutput)}`
        : `${defCoef.value} x E(${def.n})=${round4(defE)} x m(${round4(defF)})=`
          + `${round4(hpMultiplier(defF))}${def.tf.output !== 1 ? ` x trench ${def.tf.output}` : ''}`
          + `${patrolScale !== 1 ? ` x ${round4(patrolScale)} rounds on station` : ''} = ${round4(defOutput)}`,
      value: defOutput,
    });

    // 2. Attacker takes it. No fortress on the attacking side does anything
    //    in this model, because nobody has measured one.
    const atkLostThis = Math.min(defOutput, atk.pool);
    // Deaths come from the per-row split, because a mixture's rows have
    // different per-unit HP and a stack-level division would be meaningless.
    const atkAlloc = allocate(atk, atkLostThis);
    let atkDeathsThis = 0;
    for (const pt of atkAlloc.parts) {
      const d = pt.row.perUnitMaxHP ? Math.floor(pt.share / pt.row.perUnitMaxHP) : 0;
      pt.row.hpLost += pt.share;
      pt.row.deaths += d;
      atkDeathsThis += d;
    }
    if (atk.rows.length > 1) {
      derivation.push({
        label: `${tag}Attacker damage split across rows`,
        formula: 'in proportion to (attack value x count) — measured exactly on '
          + `four mixtures: ${atkAlloc.parts.map((pt) => `${pt.row.unit.code} `
            + `${round4(pt.share)}`).join(', ')}`,
        value: atkLostThis,
      });
      if (atkAlloc.overflow) {
        caveats.push('A unit row was destroyed and the surplus damage was passed '
          + 'to the others. No measured mixture ever saturated a single row, so '
          + 'what the game really does with the remainder is unknown.');
      }
    }
    if (atkLostThis < defOutput - EPS) {
      derivation.push({
        label: `${tag}Attacker loss capped by pool`,
        formula: `incoming ${round4(defOutput)} exceeds the remaining pool ${round4(atk.pool)}; the `
          + 'stack is wiped. A wiped land stack still deals its full damage (measured).',
        value: atkLostThis,
      });
    }
    derivation.push({
      label: `${tag}Attacker HP lost`,
      formula: `min(defender output ${round4(defOutput)}, pool ${round4(atk.pool)}) = ${round4(atkLostThis)}`,
      value: atkLostThis,
    });
    derivation.push({
      label: `${tag}Attacker deaths`,
      formula: `floor(${round4(atkLostThis)} / ${round4(atk.perUnitMaxHP)}) = ${atkDeathsThis}`,
      value: atkDeathsThis,
    });

    // 3. Attacker's output. Air attacking ground is evaluated on its state
    //    AFTER that incoming fire; everything else is pre-round.
    let atkOutput = null;
    if (patrol.applies) {
      // PATROL. Same base stat as a strike; only a fraction c of the stack's
      // own losses is charged against its output, against the full fraction a
      // strike pays. c is a band, not a number -- see the caveat above.
      const fLost = atk.pool > EPS ? atkLostThis / atk.pool : 0;
      const factor = Math.max(0, 1 - patrol.c * fLost);
      const lo = Math.max(0, 1 - patrol.range[1] * fLost);
      const hi = Math.max(0, 1 - patrol.range[0] * fLost);
      atkOutput = atkCoef.value * atkE * hpMultiplier(atkF) * factor * patrolScale;
      derivation.push({
        label: `${tag}Attacker output (patrol)`,
        formula: `${atkCoef.value} x E(${atk.n})=${round4(atkE)} x m(${round4(atkF)})=`
          + `${round4(hpMultiplier(atkF))} x (1 - ${patrol.c} x ${round4(fLost)})=${round4(factor)}`
          + `${patrolScale !== 1 ? ` x ${round4(patrolScale)} rounds` : ''} = ${round4(atkOutput)}`
          + ` — patrol charges only part of the attacker's own losses [estimated: c in `
          + `${patrol.range[0]}-${patrol.range[1]} gives ${round4(atkCoef.value * atkE * hpMultiplier(atkF) * lo * patrolScale)}`
          + `-${round4(atkCoef.value * atkE * hpMultiplier(atkF) * hi * patrolScale)}]`,
        value: atkOutput,
      });
      if (atk.n > 20) {
        caveats.push('Every patrol cell measured used a 10-unit air stack, where E(n) = n. '
          + 'Above 20 the size factor and the attrition band interact in a way nobody has read.');
      }
    } else if (attenuated) {
      const nAlive = atk.n - atkDeathsThis;
      if (nAlive <= 0) {
        level = 'unknown';
        reasons.push('The air attacker is reduced to zero survivors, and the post-fire law has no '
          + 'measured branch there.');
        caveats.push('An air attacker with no survivors: the post-fire output law divides by the '
          + 'survivor count and nobody has measured this case. Damage dealt is withheld rather than '
          + 'guessed (a land stack wiped in the round still deals full damage, but that is a '
          + 'different, measured, code path).');
        derivation.push({
          label: `${tag}Attacker output`,
          formula: 'Withheld: the air stack has no survivors and the post-fire law is undefined there.',
          value: null,
        });
      } else {
        const fAfter = (atk.pool - atkLostThis) / (nAlive * atk.perUnitMaxHP);
        const aliveE = effectiveUnits(nAlive);
        atkOutput = atkCoef.value * aliveE * hpMultiplier(fAfter);
        derivation.push({
          label: `${tag}Attacker output (post-fire, air vs ground)`,
          formula: `${atkCoef.value} x E(${nAlive})=${round4(aliveE)} x m(${round4(fAfter)})=`
            + `${round4(hpMultiplier(fAfter))} = ${round4(atkOutput)} — an air attacker's output is `
            + 'computed AFTER the round\'s incoming fire (measured: 30 cells, worst residual 0.005 HP)',
          value: atkOutput,
        });
        if (atk.n > 20) {
          level = worst(level, 'estimated');
          caveats.push('Every attenuated air stack ever measured was 10 units, where E(n) = n. '
            + 'Above 20 units, E(survivors) and a per-unit sum of m(f) disagree and nothing in the '
            + 'record decides between them.');
        }
      }
    } else {
      const atkParts = stackOutput(atk, (u) => attackCoefficient(u, def.unit).value, 1);
      atkOutput = atkParts.total === null ? null : atkParts.total;
      if ((atk.rows.length > 1 || atk.hero) && atkOutput !== null) {
        for (const pt of atkParts.parts) {
          // A hero part carries no row. The defender's loop has always
          // handled that; this one did not, and an attacking hero beside a
          // second unit row read pt.row.unit off undefined.
          if (pt.hero) {
            derivation.push({
              label: `${tag}Attacker hero: ${atk.hero.def.label}`,
              formula: `${pt.coef} attack x ${round4(pt.mul)} effective = `
                + `${round4(pt.out)} — fights as one unit, sitting `
                + `${atk.hero.def.sits} in the stack`
                + (atk.hero.buffedRows
                  ? `; it also multiplies ${atk.hero.buffedRows} row(s) of the stack`
                  : '; it buffs no unit type in this stack (measured)'),
              value: pt.out,
            });
            continue;
          }
          derivation.push({
            label: `${tag}Attacker output: ${pt.row.unit.label}`,
            formula: `${pt.coef} x ${round4(pt.row.effective)} effective x `
              + `m(${round4(pt.row.hpPct / 100)})=${round4(pt.mul)}`
              + (pt.heroM && pt.heroM !== 1 ? ` x hero ${round4(pt.heroM)}` : '')
              + ` = ${round4(pt.out)}`,
            value: pt.out,
          });
        }
      }
      derivation.push({
        label: `${tag}Attacker output (pre-round)`,
        formula: `${atkCoef.value} x E(${atk.n})=${round4(atkE)} x m(${round4(atkF)})=`
          + `${round4(hpMultiplier(atkF))} = ${round4(atkOutput)}`,
        value: atkOutput,
      });
    }

    // 4. Fortress DR, from the fortress's HP at ROUND START.
    let dr = 0;
    if (fort) {
      dr = fortressDR(fort.hp);
      derivation.push({
        label: `${tag}Fortress damage reduction`,
        formula: `0.15 x (${round4(fort.hp)} / 50 + 1) = ${round4(dr)} — from the fortress's HP at `
          + 'the START of the round (measured)',
        value: dr,
      });
    }

    let defLostThis = 0;
    if (atkOutput !== null) {
      const delivered = atkOutput * (1 - dr);
      defLostThis = Math.min(delivered, def.pool);
      derivation.push({
        label: `${tag}Defender HP lost`,
        formula: dr > 0
          ? `min(${round4(atkOutput)} x (1 - ${round4(dr)}) = ${round4(delivered)}, pool ${round4(def.pool)}) = ${round4(defLostThis)}`
          : `min(attacker output ${round4(atkOutput)}, pool ${round4(def.pool)}) = ${round4(defLostThis)}`,
        value: defLostThis,
      });
      atk.damageDealt += delivered;
      atk.outputRaw += atkOutput;
    } else {
      // The attacker's output has no measured value for this round, so the
      // defender's loss is UNKNOWN — not zero. Reporting 0 here would be the
      // engine asserting the defender took nothing, which is an invention.
      def.withheldLoss = true;
      atk.withheldDealt = true;
      derivation.push({
        label: `${tag}Defender HP lost`,
        formula: 'Withheld, NOT zero: the attacker\'s output has no measured value for this round, '
          + 'so how much the defender lost is unknown.',
        value: null,
      });
    }
    const defAlloc = allocate(def, defLostThis);
    let defDeathsThis = 0;
    for (const pt of defAlloc.parts) {
      const d = pt.row.perUnitMaxHP ? Math.floor(pt.share / pt.row.perUnitMaxHP) : 0;
      pt.row.hpLost += pt.share;
      pt.row.deaths += d;
      defDeathsThis += d;
    }
    if (def.rows.length > 1 && !def.withheldLoss) {
      derivation.push({
        label: `${tag}Defender damage split across rows`,
        formula: 'in proportion to (attack value x count) — measured exactly on '
          + `four mixtures: ${defAlloc.parts.map((pt) => `${pt.row.unit.code} `
            + `${round4(pt.share)}`).join(', ')}`,
        value: defLostThis,
      });
      if (defAlloc.overflow) {
        caveats.push('A defending unit row was destroyed and the surplus damage '
          + 'was passed to the others. No measured mixture ever saturated a '
          + 'single row, so the remainder rule is unknown.');
      }
    }
    derivation.push({
      label: `${tag}Defender deaths`,
      formula: def.withheldLoss
        ? 'Withheld: the defender\'s loss for this round is unknown, so its deaths are too.'
        : `floor(${round4(defLostThis)} / ${round4(def.perUnitMaxHP)}) = ${defDeathsThis}`
          + (def.tf.pool !== 1 ? ' (per-unit HP is the trench-inflated figure — measured)' : ''),
      value: def.withheldLoss ? null : defDeathsThis,
    });

    // 5. Building damage — additive, NOT carved out of unit damage and NOT
    //    reduced by the fortress's own DR (both measured).
    if (def.buildings.length && bdRate !== undefined && atkOutput !== null) {
      const bDmg = bdRate * atkE * hpMultiplier(atkF);
      const target = def.buildings[0];
      derivation.push({
        label: `${tag}Damage to ${target.label}`,
        formula: `${bdRate} per effective unit x E(${atk.n})=${round4(atkE)} = ${round4(bDmg)} — `
          + 'additive, not carved out of the damage to units, and not reduced by fortress DR (measured)',
        value: bDmg,
      });
      def.damageToBuildings = (def.damageToBuildings || 0) + bDmg;
      atk.damageToBuildings = def.damageToBuildings;
      if (target.hp !== null) {
        const applied = Math.min(bDmg, target.hp);
        target.hp -= applied;
        target.hpLost += applied;
        if (target.hp <= EPS) {
          target.destroyed = true;
          if (target.mitigates) {
            caveats.push('The fortress is destroyed. What a fortress at zero HP confers was never '
              + 'measured — the formula\'s "+1" term would still say 15%, and this engine says 0%.');
          }
        }
      }
    }

    // 6. Apply the round.
    atk.hpLost += atkLostThis;
    atk.pool -= atkLostThis;
    atk.deaths += atkDeathsThis;
    def.hpLost += defLostThis;
    def.pool -= defLostThis;
    def.deaths += defDeathsThis;
    def.damageDealt += defOutput;
    def.outputRaw += defOutput;

    for (const side of [atk, def]) {
      if (side.pool <= EPS) {
        side.pool = 0;
        side.wiped = true;
        if (side.deaths < side.n0) {
          caveats.push(`${side.label}: the stack is wiped (0 HP) but the measured death rule, `
            + `floor(HP lost / per-unit HP), gives only ${side.deaths} of ${side.n0}. Whether the `
            + 'site clamps the death count for a wiped damaged stack was never read — the '
            + 'hp_scaling rows record no death figure.');
        }
        side.n = 0;
      } else {
        side.n = Math.max(0, side.n0 - side.deaths);
      }
    }

    if (def.withheldLoss) {
      if (rounds > 1) {
        derivation.push({
          label: 'Battle stopped',
          formula: `Round ${r} produced an unmeasured quantity, so rounds ${r + 1}..${rounds} would `
            + 'be built on a guess. The battle is not carried further.',
          value: null,
        });
      }
      break;
    }
  }

  return {
    attacker: sideResult(atk, false),
    defender: sideResult(def, false),
    coverage: { level, reason: reasons.join(' '), caveats, pairs: matchup.pairs || [] },
    derivation,
  };
}

/**
 * A stack's output, summed over its rows. Each row contributes
 *     coefficient(row unit vs opponent) x effective_i x m(row HP fraction)
 * with effective_i already carrying the cumulative roster-order saturation.
 * For a single row this is exactly coefficient x E(n) x m(f), unchanged.
 */
function stackOutput(side, coefFor, scale, mulEach) {
  const k = (typeof scale === 'number' && Number.isFinite(scale)) ? scale : 1;
  const hero = side.hero;
  // A hero takes a slot in the saturating stack, so the units' effective
  // counts must be recomputed with it present -- and the hero's own share is
  // whatever the saturation leaves at its position. `maeve` sits after the
  // units and gets E(n+1)-E(n), which is exactly zero on a full stack.
  const n = side.n;
  let heroEff = 0;
  let unitScale = 1;
  if (hero) {
    if (hero.def.sits === 'first') {
      heroEff = 1;
      unitScale = n > 0 ? (effectiveUnits(n + 1) - 1) / effectiveUnits(n) : 1;
    } else {
      heroEff = effectiveUnits(n + 1) - effectiveUnits(n);
      unitScale = 1;
    }
  }
  // Per unit type, not per stack — see makeSide.
  const mFor = (unit) => {
    if (!hero || !hero.buffs) return 1;
    const b = hero.buffs[unit && unit.code];
    return b && typeof b.m === 'number' ? b.m : 1;
  };
  let total = 0;
  const parts = [];
  if (hero) {
    const heroOut = hero.atk * heroEff * k;
    hero.heroEff = heroEff;
    hero.dealt = heroOut;
    total += heroOut;
    parts.push({ hero: true, coef: hero.atk, mul: heroEff, out: heroOut });
  }
  for (const r of side.rows) {
    const c = coefFor(r.unit);
    if (c === null || c === undefined) return { total: null, parts: [] };
    const mm = mulEach ? mulEach(r) : hpMultiplier(r.hpPct / 100);
    // The stack-level multipliers (trench output, patrol duration) must be
    // carried onto the ROWS as well, or the rows no longer sum to the stack.
    // They did not, and the UI's row-vs-total sanity check caught it: a
    // defender on trench 10 reported rows totalling 141.67 against a stack
    // figure of 218.17, the same number times the 1.54 trench bonus.
    const out = c * r.effective * unitScale * mm * mFor(r.unit) * k;
    r.damageDealt = out;
    total += out;
    parts.push({ row: r, coef: c, mul: mm, out, heroM: mFor(r.unit) });
  }
  return { total, parts };
}

/**
 * Split incoming damage across a stack's rows in proportion to
 * (attack value x count), then take deaths per row from that row's own
 * per-unit HP. Measured exactly across four mixtures; allocation by pool or
 * by attack-value-alone both fail, the latter in the wrong direction.
 */
function allocate(side, incoming) {
  const w = allocationWeights(side.rows);
  const sum = w.reduce((a, b) => a + b, 0);
  const out = [];
  let spare = 0;
  side.rows.forEach((r, i) => {
    const want = sum > 0 ? incoming * (w[i] / sum) : incoming / (side.rows.length || 1);
    const got = Math.min(want, r.pool === null ? want : r.pool);
    spare += want - got;
    out.push({ row: r, share: got });
  });
  // A row that cannot absorb its share passes the remainder on. Unmeasured --
  // no measured mixture ever saturated a single row -- so it is flagged.
  if (spare > EPS) {
    for (const o of out) {
      if (spare <= EPS) break;
      const room = (o.row.pool === null) ? 0 : o.row.pool - o.share;
      const take = Math.min(room, spare);
      o.share += take;
      spare -= take;
    }
  }
  return { parts: out, overflow: spare > EPS };
}

function sideResult(side, withheld) {
  const poolStart = side.poolFull === null ? null : side.poolFull * (side.hpPct / 100);
  if (withheld) {
    return {
      rows: (side.rows || []).map((r) => ({
        unit: r.unit ? r.unit.code : null,
        label: r.unit ? r.unit.label : null,
        count: r.count, hpPct: r.hpPct, effective: r.effective, pool: r.pool,
        hpLost: null, deaths: null, unitsLeft: null, damageDealt: null,
        saturated: Math.abs(r.effective - r.count) > 0.01,
      })),
      pool: poolStart, hpLost: null, pctLost: null, deaths: null,
      unitsLeft: null, damageDealt: null, wiped: false,
      outputRaw: null, damageToBuildings: null,
      buildings: side.buildings,
    };
  }
  // A side whose loss could not be computed reports null, never 0. Zero would
  // be the engine asserting it took no damage, which is an invention.
  const lossUnknown = !!side.withheldLoss;
  // The hero belongs in rows[]. It contributes to the stack's output, and the
  // game counts it as part of the stack (its loss appears in the summary table,
  // unlike a building's). Leaving it out made the rows stop summing to their
  // own stack, which the UI's row-vs-total check caught immediately.
  //
  // hpLost and deaths are null, not 0: the hero DOES take damage -- every hero
  // measured lost exactly 2.10 HP of its own pool -- but how that share is
  // decided has not been decomposed, and 0 would be a claim.
  const heroRow = side.hero ? [{
    unit: side.hero.code,
    label: side.hero.def.label,
    isHero: true,
    level: side.hero.level,
    count: 1,
    hpPct: 100,
    effective: side.hero.heroEff === undefined ? null : side.hero.heroEff,
    pool: null,
    hpLost: null,
    deaths: null,
    unitsLeft: null,
    damageDealt: withheld ? null : (side.hero.dealt === undefined ? null : side.hero.dealt),
    saturated: !!(side.hero.heroEff !== undefined && side.hero.heroEff < 0.999),
  }] : [];

  const rowsOut = heroRow.concat((side.rows || []).map((r) => ({
    unit: r.unit ? r.unit.code : null,
    label: r.unit ? r.unit.label : null,
    count: r.count,
    hpPct: r.hpPct,
    effective: r.effective,
    pool: r.pool,
    hpLost: lossUnknown ? null : r.hpLost,
    deaths: lossUnknown ? null : r.deaths,
    unitsLeft: lossUnknown ? null : Math.max(0, r.count - r.deaths),
    damageDealt: side.withheldDealt ? null : r.damageDealt,
    saturated: Math.abs(r.effective - r.count) > 0.01,
  })));
  return {
    rows: rowsOut,
    pool: poolStart,
    hpLost: lossUnknown ? null : side.hpLost,
    pctLost: lossUnknown ? null : (poolStart ? (side.hpLost / poolStart) * 100 : 0),
    deaths: lossUnknown ? null : side.deaths,
    unitsLeft: lossUnknown ? null : Math.max(0, side.n0 - side.deaths),
    damageDealt: side.withheldDealt ? null : side.damageDealt,
    wiped: lossUnknown ? false : side.wiped,
    outputRaw: side.withheldDealt ? null : side.outputRaw,
    damageToBuildings: side.withheldDealt ? null : side.damageToBuildings,
    buildings: side.buildings,
  };
}
