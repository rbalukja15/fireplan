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
  CLASS_ATTACK,
  CLASS_ATTACK_CORROBORATED,
  GROUND_DEFENCE_VS_AIR,
  CLASS_DEFENCE,
  BUILDING_DAMAGE_PER_EFFECTIVE_UNIT,
  BUILDING_DAMAGE_FLOOR,
  TRENCH_APPLIES_TO,
  EMBARKED_COEF,
  EMBARKED_MAXHP,
  EMBARKED_ATTACK,
  EMBARKED_DEFENCE,
  EMBARKED_TERRAIN,
  EMBARKED_CLASS_CHANGE_TERRAIN,
  UNIT_RANGE,
  MELEE_RANGE,
  VARIANCE_BAND,
  FORTRESS,
  PATROL,
  ROSTER_ORDER,
  TARGET_FACTOR,
  TARGET_FACTOR_DEFAULT,
  HERO_ALLOC_WEIGHT,
  MAX_UNIT_ROWS,
  STACK_GROUP,
  STACK_GROUP_LABEL,
  HEROES,
  HEROES_LAND_REFUSED,
  HEROES_OTHER_TERRAIN,
  REPAIR_COST,
  REPAIR_HOURS,
  HERO_REPAIR,
  BOMBARDMENT,
  BOMBARDMENT_SPLIT,
  HERO_REACH,
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
 *
 * TWO SEGMENTS, meeting exactly at 50 HP and 30%:
 *   hp <  10   0            the fortress confers nothing
 *   hp <= 50   0.05 + 0.005 x hp
 *   hp >  50   0.15 + 0.003 x hp, capped at 0.90
 *
 * This used to be the second line alone, which is right for every FULL
 * fortress -- 0.30/0.45/0.60/0.75/0.90 at levels 1-5 -- and wrong by up to
 * eight points for any fortress that has been battered below 50. Since every
 * fortress this project submitted was full, the low segment only ever appeared
 * in the closing rounds of a long battle, and it was chased for two sweeps as
 * a "late-round output drift" in the ATTACKER before anyone read the column
 * the site had been printing all along. See PROVENANCE['FORTRESS.dr.lowSegment'].
 *
 * The 0.90 cap is the site's, read at 250.4 and 251.3 HP where the old formula
 * would give 90.1 and 90.4. A destroyed fortress still returns 0 rather than
 * the formula's floor.
 */
export function fortressDR(fortressHP) {
  const hp = Number(fortressHP);
  if (!Number.isFinite(hp) || hp <= 0) return 0;
  if (hp < FORTRESS.inertBelowHP) return 0;
  const dr = hp <= FORTRESS.lowSegmentBelowHP
    ? FORTRESS.lowIntercept + FORTRESS.lowSlopePerHP * hp
    : FORTRESS.drSlopePer50HP * (hp / FORTRESS.hpPerLevel + 1);
  return Math.min(FORTRESS.maxDR, Math.max(0, dr));
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
  // The Balloon is excluded from the air-attacks-ground attenuation law: its
  // three readings are all from LAND terrain, where nothing is attenuated.
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
 * Any hero, from either table. HEROES holds the sixteen that fight on land and
 * HEROES_OTHER_TERRAIN the six the server refuses there -- but those six are
 * fully decomposed now, on their own terrain, attacking and defending, across
 * their level ranges. Splitting the lookup was what kept the engine applying
 * no hero effect at all on an air or naval stack.
 */
export function heroDef(code) {
  return HEROES[code] || HEROES_OTHER_TERRAIN[code] || null;
}

/**
 * A hero's stack multiplier at a given level.
 *
 * The measured points are stored verbatim and a level between them is
 * INTERPOLATED, because neither buffing hero's curve is a clean line or a
 * clean step: joffre_home is exactly 1.10 + 0.02*level from level 5 up, but
 * levels 1-4 read 1.10 / 1.15 / - / 1.16 and fit nothing. Fitting a formula
 * through that would be inventing nineteen values from eight.
 */
export function heroBuff(code, level, unitCode, side) {
  const h = heroDef(code);
  if (!h) return { m: null, exact: false, note: 'unknown hero' };
  const entry = (h.buffs || {})[unitCode];
  if (!entry) {
    const targets = Object.keys(h.buffs || {});
    return { m: 1.0, exact: true,
             note: targets.length
               ? `${h.label} buffs ${targets.join(' and ')}, not this unit type `
                 + '(measured: its excess over its own attack was zero on the '
                 + 'other seven land types)'
               : `${h.label} is a pure combat unit — it raised a nine-type `
                 + 'stack by exactly its own attack value and nothing more.' };
  }
  // A buff has a SIDE. joffre_home and kangal measure exactly 0.00 attacking
  // against an expected 6.00 and 2.40, so theirs is defence-only; alvin's and
  // hank's apply to both. Applying a defence-only buff to an attacking stack
  // was the shape of the previous model and inflates it silently.
  if (side === 'attacker' && entry.channel === 'defence') {
    return { m: 1.0, exact: true,
             note: `${h.label}'s buff is DEFENCE-ONLY — measured at exactly `
               + 'zero on an attacking stack, so it does not apply here.' };
  }
  // The mirror, which only the air and naval heroes have. Richthofen, von
  // Thaden and Hersing all measure exactly 1.0000 on a defending stack of the
  // type they buff attacking -- so the channel has both signs, and reading one
  // and assuming the other was never safe.
  if (side === 'defender' && entry.channel === 'attack') {
    return { m: 1.0, exact: true,
             note: `${h.label}'s buff is ATTACK-ONLY — measured at exactly `
               + '1.0000 on a defending stack, so it does not apply here.' };
  }
  // A buff can have a DIFFERENT curve per side, not just a side it applies on.
  // Tōgō-with-bombardment reads 1.2785 on a battleship it is attacking with
  // and exactly 1.30 on one it is defending with -- the same hero, the same
  // level, the same unit. Every other hero measured so far has one curve for
  // whichever sides it acts on, so this field is optional and `curve` stays
  // the default.
  const curve = (side === 'defender' && entry.curveDefending)
    ? entry.curveDefending : entry.curve;
  return curveAt(curve, level, h, 'output');
}

/**
 * A measured curve read at one level. Interpolated between measured points and
 * never fitted: pershing's infantry HP curve climbs to 1.70 by level 5, DROPS
 * to 1.10 at level 6 and climbs again, so no formula is right on both sides.
 */
function curveAt(curve, level, h, what) {
  if (!curve) return { m: 1.0, exact: true, note: 'no curve' };
  const lv = Math.max(1, Math.min(h.maxLevel || 20, Math.round(num(level, 1))));
  const pts = Object.keys(curve).map(Number).sort((a, b) => a - b);
  if (curve[lv] !== undefined) {
    return { m: curve[lv], exact: true, note: `measured directly at level ${lv}` };
  }
  if (pts.length === 1) {
    return { m: curve[pts[0]], exact: false,
             note: `only level ${pts[0]} was ever measured (x${curve[pts[0]]}); `
               + `level ${lv} assumes the same figure` };
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
             + `measured ${what} levels ${below} (x${curve[below]}) and `
             + `${above} (x${curve[above]})` };
}

/** A hero's multiplier on one unit type's MAX HP, at this level. */
export function heroHpBuff(code, level, unitCode) {
  const h = heroDef(code);
  if (!h || !h.hpBuffs || !h.hpBuffs[unitCode]) {
    return { m: 1.0, exact: true, note: 'no HP buff measured for this type' };
  }
  return curveAt(h.hpBuffs[unitCode], level, h, 'HP');
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
    // A row that cannot reach the target is not in the firing stack at all --
    // it neither fires nor saturates the rows that do. Measured: infantry 20 +
    // light artillery 20 firing from 20 km deals 100.00, the identical figure
    // the artillery deals alone. Counting the infantry toward E() would have
    // the stack gain output by adding units that cannot shoot.
    if (r && r.inert) { eff[i] = 0; continue; }
    const c = Math.max(0, num(r && r.count, 0));
    eff[i] = effectiveUnits(seen + c) - effectiveUnits(seen);
    seen += c;
  }
  return (rows || []).map((r, i) => ({ ...r, effective: eff[i] }));
}

/**
 * How incoming damage splits across a stack's rows:
 *
 *     weight_i = TARGET_FACTOR[unit_i] x count_i
 *
 * It is a property of the TARGET, not of the attacker -- all nine land
 * attackers produce the identical three-value pattern, bracketed across them
 * to [0.4979,0.5023], [0.7449,0.7559] and [0.9918,1.0083]. Infantry soak half
 * of what any other type takes; cavalry three quarters.
 *
 * This engine shipped "in proportion to the defending row's own attack value"
 * until 2026-08-19, which is out by 40% of the stack total on a nine-row
 * stack. It fitted because all four mixtures it came from were infantry +
 * artillery, whose own attack values are 4.0 and 8.0 -- exactly the 0.5 : 1.0
 * ratio this table gives that pair, and nothing else.
 *
 * The attacker's TOTAL is unaffected: still coefficient x E(n) whatever the
 * mix, confirmed for all nine attackers. These are allocation weights, not
 * damage values.
 */
export function allocationWeights(rows) {
  return (rows || []).map((r) => {
    const code = r && r.unit && (r.unit.code || r.unit);
    const f = TARGET_FACTOR[code] === undefined
      ? TARGET_FACTOR_DEFAULT : TARGET_FACTOR[code];
    // SURVIVORS, not the count the battle started with. A row that has lost
    // half its units draws half the fire it used to, and this used to weight
    // by r.count for the whole battle.
    //
    // Invisible in the entire record twice over: in round one nothing has died
    // yet, and in a single-type stack one row takes everything however it is
    // weighted -- and every mixed-stack reading on file is a single round. It
    // took the server's OWN post-round counts, read back through updateCounts,
    // to separate them: at round two the site splits 0.4572/0.1887/0.3542
    // across 29 infantry, 6 armoured cars and 15 cavalry, which is exactly the
    // survivor weighting, where the opening counts give 0.4828/0.1655/0.3517.
    const alive = (r && r.deaths !== undefined && r.deaths !== null)
      ? Math.max(0, num(r.count, 0) - num(r.deaths, 0))
      : num(r && r.count, 0);
    return Math.max(0, f * Math.max(0, alive));
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
export function coverageOfStacks(atkRows, defRows, defTerrain, atkTerrain) {
  const a = (atkRows || []).filter((r) => r.count > 0);
  const d = (defRows || []).filter((r) => r.count > 0);
  if (!a.length || !d.length) {
    return { level: 'unknown', reason: 'A side has no units.', pairs: [] };
  }
  const rank = { measured: 0, estimated: 1, unknown: 2 };
  const pairs = [];
  for (const ar of a) {
    for (const dr of d) {
      const c = coverageOf(ar.unit, dr.unit, defTerrain, atkTerrain);
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

export function coverageOf(atkUnit, defUnit, defTerrain, atkTerrain) {
  const a = resolveUnit(atkUnit);
  const d = resolveUnit(defUnit);

  if (!a || !d) {
    return { level: 'unknown', reason: 'Unrecognised unit code — nothing in the record applies.' };
  }
  if (a.code === 'bal' || d.code === 'bal') {
    return {
      level: 'estimated',
      reason: 'The Balloon is measured now — max HP 20.0, attack 3.0, defence 3.0 — but only in '
        + 'LAND terrain, which is the only terrain the server will run it in. Its fourteen older '
        + 'rows are empty because they were sent in air terrain, which aborts the whole request. '
        + 'Treat a Balloon result as estimated: three readings, one terrain.',
    };
  }

  // DERIVED, not hand-written. This function used to be a cascade of class
  // comparisons stating what had and had not been measured, and it went stale
  // exactly the way the standing-limits list in index.html did: it still
  // claimed "a ground stack ATTACKING air has never been measured" long after
  // the class matrix filled every land-vs-air cell, so it withheld results the
  // engine could compute. The coefficient lookups below ARE the record; asking
  // them what they have cannot drift from what they have.
  const atk = attackCoefficient(a, d, defTerrain, atkTerrain);
  const def = defenceCoefficient(d, a, defTerrain, atkTerrain);
  const rank = { measured: 0, estimated: 1, unknown: 2 };
  const worse = rank[atk.level] >= rank[def.level] ? atk : def;
  const which = worse === atk
    ? `${a.label} attacking ${d.label}` : `${d.label} defending against ${a.label}`;
  if (worse.level === 'unknown') {
    return {
      level: 'unknown',
      reason: `${which} has never been measured: ${worse.source}. The engine `
        + 'withholds the numbers rather than inventing them.',
    };
  }
  if (worse.level === 'estimated') {
    // The warning matters more than the label. A stand-in taken from a
    // same-class diagonal is not a small error bar: attack is KNOWN to vary by
    // target class -- a Bomber reads 3.0 against air and 30.0 against ground,
    // a factor of ten -- so it may vary by target unit too.
    // Two different reasons a cell can be estimated, and they carry very
    // different risks, so they say different things.
    const standIn = /diagonal stat, with no reading/.test(worse.source);
    return {
      level: 'estimated',
      reason: `${which} is a stand-in, not a reading: ${worse.source}.`
        + (standIn
          ? ' This exact off-diagonal pairing has never been submitted and no '
            + 'column covers it. Attack is known to vary by target class (the '
            + 'Bomber is 3.0 against air and 30.0 against ground), so it may '
            + 'vary by target unit too — this number could be wrong by any '
            + 'factor.'
          : ' The column it comes from rests on a single reading rather than '
            + 'on two independent ones, so it is a measurement without a '
            + 'corroboration — see the class_matrix_precision gap.'),
    };
  }
  return {
    level: 'measured',
    reason: `Both halves of ${a.label} vs ${d.label} are measured — attack from `
      + `${atk.source}, defence from ${def.source}.`,
  };
}

/**
 * The attacking side's per-effective-unit output stat against this defender.
 * { value, level, source } — value null means "no reading exists".
 */
/**
 * The class a unit FIGHTS AS, which is not always the class it is.
 *
 * Two separate things forced this into one function. First, the token spaces
 * never agreed: UNITS[].cls says 'sea' and CLASS_ATTACK's third column is
 * called 'naval'. Written out longhand at each site that comparison silently
 * failed three times -- the embarked filter matched every unit including the
 * ships, the naval-vs-air special case could never fire, and CLASS_ATTACK's
 * whole naval column was unreachable, so every land unit attacking a ship used
 * its own diagonal stat and reported "no reading" for a reading that exists.
 * Infantry against a battleship came out at 4.0 where the record says 2.0.
 *
 * Second, EMBARKATION IS A CLASS CHANGE, not a pair of stat overrides. A
 * non-naval unit in sea or debark terrain attacks at a flat 1.0, holds a flat
 * 10 HP whatever it is, AND is hit on the attacker's naval column. Measured
 * six times for six: cavalry deals 8.0 to embarked infantry and to embarked
 * fighters alike, against 15.0 on land; light artillery 1.0 against 5.0; a
 * heavy tank 23.0 against 45.0. Every one lands on the naval column exactly.
 */
/**
 * The class a unit is, before anything about the battle is taken into account.
 * Normalises UNITS[].cls 'sea' onto CLASS_ATTACK's column name 'naval', and
 * folds in the one unit whose class label does not describe how it fights.
 */
function ownClass(u, terrain) {
  const c = u.cls === 'sea' ? 'naval' : u.cls;
  if (c === 'naval') return 'naval';
  // THE BALLOON IS A LAND UNIT ON LAND, in every role. It is classed 'air' and
  // land terrain is the only terrain the server will run it in.
  //   attacking  a balloon loses 166.67 against forty infantry, which is
  //              5.0 x E(40) -- infantry's LAND defence, not their 0.4 air one
  //   as a target  twenty infantry deal 80.00 to ten balloons, which is
  //              4.0 x E(20) -- infantry's LAND attack column
  //   both at once  ten balloons against ten balloons, 30.00 each way, which
  //              is 3.0 x E(10) -- the balloon's own land column
  // Writing this on the attacking side only made a balloon duel come out at
  // 200.00 against a measured 60.00, because the attacker then read its air
  // column against a target it was standing next to on the ground.
  if (u.code === 'bal' && terrain === 'land') return 'land';
  return c;
}

export function combatClass(unit, terrain) {
  const u = resolveUnit(unit);
  if (!u) return null;
  const own = ownClass(u, terrain);
  if (own === 'naval') return 'naval';
  // SEA only, not debark. A unit in debark still attacks on the embarked
  // column and still holds the flat 10 HP -- that is EMBARKED_TERRAIN, and it
  // covers both -- but as a TARGET it is hit on the attacker's LAND column.
  // Treating the two terrains as one made a light artillery attacker 5x wrong.
  if (EMBARKED_CLASS_CHANGE_TERRAIN.includes(terrain)) return 'naval';
  return own;
}

/**
 * The class an ATTACKER sees its target as. The same for everyone.
 *
 * This function briefly carried an exemption saying an AIR attacker is blind
 * to embarkation, on the strength of a fighter dealing 98.89 to a hundred
 * infantry on land and 98.61 to the same hundred at sea. The two columns it
 * was meant to distinguish are int.land = 5.0 and int.naval = 5.0. They are
 * the same number, so that pair of readings could not have discriminated
 * anything, and reading "no difference" as "blind to the difference" invented
 * an asymmetry out of a test with no power.
 *
 * The cell that does discriminate is an air stack against EMBARKED FIGHTERS,
 * where the columns are 20.0 and 5.0. Twenty fighters deal 98.61 to two
 * hundred embarked fighters, which is 5.0 x E(20) x m(0.98542) -- the naval
 * column, attenuated. Everyone sees embarkation, and the rule is uniform.
 */
export function targetClassFor(attacker, target, targetTerrain) {
  const t = resolveUnit(target);
  if (!resolveUnit(attacker) || !t) return null;
  return combatClass(t, targetTerrain);
}

export function attackCoefficient(atkUnit, defUnit, defTerrain, atkTerrain) {
  const a = resolveUnit(atkUnit);
  const d = resolveUnit(defUnit);
  if (!a || !d) return { value: null, level: 'unknown', source: 'unrecognised unit' };
  // The whole matrix is measured now: a unit's coefficient is flat across
  // targets within a class and changes only between classes, so one lookup by
  // the TARGET'S CLASS covers every pairing. This used to fall through to
  // "no reading for air attacking naval" and withhold a number.
  const row = CLASS_ATTACK[a.code];
  const dCls = targetClassFor(a, d, defTerrain);
  const aCls = combatClass(a, atkTerrain);
  const v = row ? row[dCls] : undefined;
  if (v !== undefined) {
    const sameClass = aCls === dCls;
    const embarked = dCls === 'naval' && d.cls !== 'sea';
    return {
      value: v,
      // Corroboration is a property of the RECORD, so it is read from the
      // record rather than inferred from the attacker's class here. A blanket
      // "air attackers are estimated" was tried and was wrong both ways at
      // once: it understated the fliers' thirty-cell land column and their
      // four-run diagonal, and said nothing about the single-cell land-vs-air
      // and naval columns that genuinely do rest on one reading each.
      level: (a.code === 'bal') ? 'estimated'
        : CLASS_ATTACK_CORROBORATED.some(([x, y]) => x === aCls && y === dCls)
          ? 'measured' : 'estimated',
      source: embarked
        ? `CLASS_ATTACK (${aCls} attacking an EMBARKED ${d.label}, which is hit `
          + 'on the naval column — measured six ways for six)'
        : sameClass
          ? `CLASS_ATTACK (${aCls} vs ${aCls}; flat across every target in the class)`
          : `CLASS_ATTACK (${aCls} attacking ${dCls}, measured directly)`,
    };
  }
  if (a.atk === null) {
    return { value: null, level: 'unknown', source: `${a.code} has no measured attack` };
  }
  return { value: a.atk, level: 'estimated',
           source: `${a.label}'s diagonal stat, with no reading for ${dCls} targets` };
}

/**
 * The defending side's per-effective-unit output stat against this attacker.
 */
export function defenceCoefficient(defUnit, atkUnit, defTerrain, atkTerrain) {
  const d = resolveUnit(defUnit);
  const a = resolveUnit(atkUnit);
  if (!a || !d) return { value: null, level: 'unknown', source: 'unrecognised unit' };
  const dCls = targetClassFor(a, d, defTerrain);
  const aCls = combatClass(a, atkTerrain);
  // An EMBARKED defender deals a flat 1.0 per effective unit, whatever it is
  // and whatever is shooting at it -- 40 embarked fighters answer 20 infantry
  // with exactly 1.0 x E(40) = 33.33. That is a reading, so a pairing that is
  // otherwise unmeasured stops being unknown the moment the defender puts to
  // sea.
  if (dCls === 'naval' && d.cls !== 'sea') {
    const v = EMBARKED_DEFENCE[aCls];
    if (v !== undefined) {
      return { value: v, level: 'measured',
               source: `an embarked ${d.label} defends at ${v} against `
                 + `${aCls} attackers (EMBARKED_DEFENCE)` };
    }
  }
  // CLASS_DEFENCE is the whole table now: two attackers of each class against
  // every defender, every cell agreeing between them. The cascade of special
  // cases this replaced could only answer same-class pairings and air-attacks-
  // ground, and returned "no reading" for everything else -- which withheld
  // the entire battle, not just half of it.
  const row = CLASS_DEFENCE[d.code];
  const v = row ? row[aCls] : undefined;
  if (v !== undefined) {
    return {
      value: v,
      level: 'measured',
      source: `CLASS_DEFENCE (${d.label} against ${aCls} attackers; two `
        + 'independent attackers of that class read the same figure)',
    };
  }
  if (d.def === null) return { value: null, level: 'unknown', source: `${d.code} has no measured defence` };
  return { value: null, level: 'unknown', source: `no reading for ${dCls} defending against ${aCls}` };
}

// ---------------------------------------------------------------------------
// simulate()
// ---------------------------------------------------------------------------

function num(v, fallback) {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}

function makeSide(cfg, role, derivation, caveats, battle) {
  let side_groupConflict = null;
  let side_hero = null;
  const label = role === 'attacker' ? 'Attacker' : 'Defender';
  const tf = trenchFactors(cfg && cfg.trench);

  // A stack is a MIXTURE of distinct unit types. The single-unit form is one
  // row; everything below works the same either way, and for one row the
  // per-row arithmetic reduces exactly to what it was before.
  const rawRows = (cfg && Array.isArray(cfg.rows) && cfg.rows.length)
    ? cfg.rows : null;
  // RANGE, ROW BY ROW. Only the ATTACKER's reach decides anything: a defender
  // never initiates, however far it could shoot (infantry attacking light
  // artillery from 20 km produces no battle, though the artillery reaches 30).
  // So the defender's rows are never gated -- they are targets at any distance
  // the attacker can cross.
  const preRows = normaliseRows(cfg);
  const dist = Math.max(0, num(battle && battle.distance, 0));
  const unreachable = [];
  if (role === 'attacker' && dist > 0) {
    for (const r of preRows) {
      const reach = UNIT_RANGE[r.unit && r.unit.code];
      if (reach !== undefined && dist > reach) {
        r.inert = true;
        unreachable.push(`${r.unit.label} (${reach} km)`);
      }
    }
  }
  const rows = effectiveByRow(preRows, role === 'attacker' ? 'atk' : 'def');
  if (unreachable.length) {
    const all = unreachable.length === rows.length;
    caveats.push(`${label}: ${unreachable.join(', ')} cannot reach a target at `
      + `${dist} km.` + (all
        ? ' Nothing in this stack reaches it, so there is no battle at all.'
        : ' Those rows are inert — they neither fire nor count toward the '
          + 'stack-size factor for the rows that do.'));
    derivation.push({
      label: `${label} out of reach`,
      formula: `${unreachable.join(', ')} at ${dist} km. Measured: a mixed `
        + 'stack of 20 infantry and 20 light artillery firing from 20 km deals '
        + '100.00 — exactly what the artillery deals alone.',
      value: null,
    });
  }
  const dropped = rawRows
    ? rawRows.length - preRows.length : 0;
  if (dropped > 0) {
    caveats.push(`${label}: ${dropped} unit row(s) dropped. A stack cannot hold `
      + 'the same unit type twice — the server refuses it outright — and an '
      + 'unrecognised unit has no constants.');
  }

  // Pools are computed AFTER the hero block below, because a hero can raise a
  // unit type's max HP and the pool has to include that.
  const computePools = () => {
    for (const r of rows) {
      // TRENCHES ARE INFANTRY-ONLY. Heavy tanks, artillery and cavalry read
      // the identical pool and the identical output at trench 0 and trench 10;
      // only infantry move. This engine applied both multipliers to every unit
      // type, which inflates a dug-in tank stack by up to 35% of pool and 75%
      // of output.
      // The POOL bonus applies to whichever side is dug in; the OUTPUT bonus
      // was only ever measured on a DEFENDER, and an attacker in a trench
      // deals exactly what it deals outside one.
      const digsIn = TRENCH_APPLIES_TO.includes(r.unit && r.unit.code);
      r.trenchPool = digsIn ? tf.pool : 1;
      r.trenchOutput = (digsIn && role === 'defender') ? tf.output : 1;
      // EMBARKED UNITS HOLD A FLAT 10 HP, read straight off the pools: 20
      // heavy tanks at sea report 200.0, not 5194.8, and so do 20 infantry,
      // 20 cavalry, 20 fighters and 20 bombers. The app modelled the flat 1.0
      // attack and missed this entirely, so every embarked pool it drew was
      // wrong -- by 26x for a heavy tank. It is also what censored the
      // naval-vs-air reading: a target stack sized off the unit table's max HP
      // is six times smaller than intended the moment it puts to sea.
      const embarkedHP = r.embarked ? EMBARKED_MAXHP : null;
      r.perUnitMaxHP = embarkedHP !== null
        ? embarkedHP * r.trenchPool * (r.hpBuff || 1)
        : ((r.unit && r.unit.maxHP !== null)
          ? r.unit.maxHP * r.trenchPool * (r.hpBuff || 1) : null);
      r.poolFull = r.perUnitMaxHP === null ? null : r.count * r.perUnitMaxHP;
      r.pool = r.poolFull === null ? null : r.poolFull * (r.hpPct / 100);
      r.hpLost = 0;
      r.deaths = 0;
      // null, not 0. A path that cannot decompose the stack's output per row --
      // the air and patrol laws work on whole-stack survivors -- must say it
      // has no figure. Zero is a claim, and it was a false one.
      r.damageDealt = null;
    }
  };
  computePools();

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

  // This side's terrain. Declared here because the hero block below needs it:
  // the six air/naval heroes are gated on terrain rather than on ignorance.
  const myTerrain = (role === 'defender' && battle && battle.defenderTerrain)
    ? battle.defenderTerrain : (battle && battle.terrain);

  // THE HERO. One per stack (addHero refuses a second). It fights as a single
  // unit at its own attack value, and multiplies what the rest of the stack
  // deals. Where it sits is measured per hero and changes both effective
  // counts, because the stack saturates cumulatively in roster order.
  const heroCfg = cfg && cfg.hero;
  let hero = null;
  if (heroCfg && heroCfg.code) {
    // Both tables, one lookup. The six air/naval heroes are decomposed now --
    // own attack, per-level curves, and a buff channel that has BOTH signs --
    // so there is nothing left to refuse them for. What is still checked is
    // the TERRAIN: the server will not put Hersing on land, and neither will
    // this. `refused` now means "wrong terrain for this hero", not "unknown".
    const known = heroDef(heroCfg.code);
    const other = HEROES_OTHER_TERRAIN[heroCfg.code];
    // GATED ON THE STACK, not on the terrain field. A naval hero is refused
    // because it cannot stand with land units -- "Can't have Otto Hersing on
    // land" is about the company it keeps. Fighters DEFENDING over land are
    // still an air stack and Richthofen applies to them, which is exactly how
    // every air-hero reading was taken: atk_terrain air, def_terrain land.
    // Gating on terrain instead silently dropped the hero from a hundred
    // measured cells.
    const groupsNow = stackGroupsOf(rows);
    const wrongStack = other && !(groupsNow.length === 1
      && ((other.terrain === 'air' && groupsNow[0] === 'air')
        || (other.terrain === 'sea' && groupsNow[0] === 'sea')));
    const refused = wrongStack ? other : null;
    if (known && !wrongStack) {
      const lvl = Math.max(1, Math.min(known.maxLevel,
        Math.round(num(heroCfg.level, 1))));
      // Two things no land hero does, so two things the shape did not carry.
      // Richthofen's and Tōgō-with-bombardment's OWN ATTACK moves with level
      // (25 to 125 for Richthofen), and Hersing's POOL does (100 to 200.7).
      // Every land hero is flat in both, which is why the fields are optional
      // and the scalar stays the fallback.
      const ownCurve = known.atkAttackingCurve;
      const poolCurve = known.poolCurve;
      if (num(heroCfg.level, 1) > known.maxLevel) {
        caveats.push(`${label}: ${known.label} caps at level ${known.maxLevel} — `
          + `the server states so outright and refuses anything higher, even `
          + `though the form offers 1-20 for every hero. Clamped.`);
      }
      // THE HP CHANNEL, now modelled rather than disclosed. A hero can raise
      // one unit type's MAX HP, on a curve of its own, read exactly off the
      // server's refusal. This used to be a caveat saying "the pools below are
      // too LOW"; it is now simply applied.
      const hpHits = [];
      for (const r of rows) {
        const b = heroHpBuff(heroCfg.code, lvl, r.unit.code);
        if (b.m !== 1) {
          r.hpBuff = b.m;
          r.hpBuffExact = b.exact;
          hpHits.push({ row: r, b });
        }
      }
      // Output buffs are per unit type AND per side.
      const buffs = {};
      let anyInexact = null;
      for (const r of rows) {
        const b = heroBuff(heroCfg.code, lvl, r.unit.code, role);
        buffs[r.unit.code] = b;
        if (b.m !== 1 && !b.exact) anyInexact = b;
      }
      for (const h of hpHits) if (!h.b.exact) anyInexact = h.b;
      const hitOut = rows.filter((r) => buffs[r.unit.code].m !== 1);
      const ownAtk = (role === 'attacker' && ownCurve)
        ? curveAt(ownCurve, lvl, known, 'own attack').m
        : (role === 'attacker' ? known.atkAttacking : known.atkDefending);
      const ownPool = poolCurve
        ? curveAt(poolCurve, lvl, known, 'pool').m : known.pool;
      // A HERO'S OWN OUTPUT SCALES WITH ITS OWN HP, by the same m(f) every
      // unit obeys. Every hero reading in this project set the hero to 100%
      // and never varied it, so the question was never asked. Tōgō contributes
      // 15.00 at full health, 7.88 at 50% and 2.17 at 10% -- which is
      // 15.0 x 0.525 and 15.0 x 0.145 to the printed decimal. Lawrence and
      // Kangal reproduce it exactly too. The BUFF does not scale: Pershing's
      // constant 12.00 on an infantry stack is the same at 25% as at 100%.
      const heroPct = Math.max(0, Math.min(100,
        num(heroCfg.hpPct === undefined ? 100 : heroCfg.hpPct, 100)));
      hero = { code: heroCfg.code, def: known, level: lvl,
               atk: ownAtk * hpMultiplier(heroPct / 100),
               atkFull: ownAtk, hpPct: heroPct,
               pool: ownPool * (heroPct / 100), poolFull: ownPool, buffs,
               buffedRows: hitOut.length, hpHits: hpHits.length };
      if (heroPct !== 100) {
        derivation.push({
          label: `${label} hero at ${heroPct}% HP`,
          formula: `${known.label} contributes ${round4(ownAtk)} x `
            + `m(${round4(heroPct / 100)})=${round4(hpMultiplier(heroPct / 100))} = `
            + `${round4(hero.atk)}. A hero's own output scales with its own HP `
            + 'exactly as a unit\'s does (measured); its BUFF does not.',
          value: hero.atk,
        });
      }
      if (ownCurve && role === 'attacker') {
        derivation.push({
          label: `${label} hero own attack`,
          formula: `${known.label}'s own attack MOVES WITH LEVEL, which no land `
            + `hero's does: ${ownCurve[1]} at level 1 and `
            + `${ownCurve[known.maxLevel]} at ${known.maxLevel}. At level `
            + `${lvl} it is ${round4(ownAtk)}.`,
          value: ownAtk,
        });
      }
      if (poolCurve) {
        derivation.push({
          label: `${label} hero pool`,
          formula: `${known.label}'s own HP MOVES WITH LEVEL, which no land `
            + `hero's does: ${poolCurve[1]} at level 1 and `
            + `${poolCurve[known.maxLevel]} at ${known.maxLevel}.`,
          value: ownPool,
        });
      }
      if (hitOut.length) {
        derivation.push({
          label: `${label} hero output buff`,
          formula: hitOut.map((r) => `${r.unit.label} x`
            + `${round4(buffs[r.unit.code].m)}`).join(', ')
            + ` — ${known.label} at level ${lvl}; every other row is unbuffed`,
          value: buffs[hitOut[0].unit.code].m,
        });
      }
      const suppressed = rows.filter((r) => /DEFENCE-ONLY/.test(
        buffs[r.unit.code].note || ''));
      if (suppressed.length) {
        derivation.push({
          label: `${label} hero buff does not apply`,
          formula: `${known.label}'s multiplier is DEFENCE-ONLY — measured at `
            + 'exactly 0.00 on an attacking stack — so it is not applied to '
            + `${suppressed.map((r) => r.unit.label).join(', ')}`,
          value: 1,
        });
      }
      if (hpHits.length) {
        derivation.push({
          label: `${label} hero HP buff`,
          formula: hpHits.map((h) => `${h.row.unit.label} max HP x`
            + `${round4(h.b.m)}`).join(', ')
            + ` — a separate channel from the output buff, read off the `
            + `server's own refusal, so exact`,
          value: hpHits[0].b.m,
        });
      }
      if (anyInexact) {
        hero.interpolated = true;
        caveats.push(`${label}: ${known.label} — ${anyInexact.note}.`);
      }
      // THIS USED TO DECLARE A HERO WHOSE OWN CONTRIBUTION IS NOT A CONSTANT,
      // and quote a band of 37.99 to 64.90 because thirty-four requests had
      // not found the rule. There was no such hero. Tōgō-with-bombardment and
      // Lucien-with-gas carry an ABILITY -- a second damage source with its
      // own duration, its own range and its own blast radius -- and what moved
      // was the share of it the target absorbed. Their own attacks are flat,
      // 15.00 and 8.00, exactly like the plain versions they differ from.
      //
      // The ability is computed per round in the loop below; here the hero is
      // simply told the reader about, because a stack carrying one behaves in
      // ways the rest of this model does not prepare anyone for: it damages
      // its OWN side, it keeps firing when the stack is out of range, and its
      // effect on the enemy goes UP as the enemy moves further away.
      const ability = BOMBARDMENT[known.code] || BOMBARDMENT[heroCfg.code];
      if (ability && role === 'attacker') {
        hero.ability = ability;
        caveats.push(`${label}: ${known.label} carries an ability, not just an `
          + `attack. It adds a second damage source centred on the TARGET, for `
          + `${ability.rounds} rounds, and every stack inside its blast shares `
          + `it — including this one, and including anything friendly standing `
          + `there. Moving the target further away can therefore INCREASE what `
          + `the target loses, because past the blast the attacker stops `
          + `absorbing part of it.`);
      }
    } else if (refused) {
      // WRONG TERRAIN, which is a refusal by the server and not a gap in the
      // record. These six are fully decomposed on their own terrain now; what
      // remains true is that the server will not put Hersing on land.
      hero = { code: heroCfg.code, refused };
      caveats.push(`${label}: ${refused.label} — ${refused.why} It is fully `
        + `measured on ${refused.terrain === 'air' ? 'an AIR' : 'a NAVAL'} `
        + `stack — attacking and defending, across its whole level range — but `
        + `this stack is not one, so it is not applied here.`);
    } else {
      caveats.push(`${label}: unrecognised hero "${heroCfg.code}" ignored.`);
    }
  }
  side_hero = hero && hero.def ? hero : null;
  if (side_hero) side_hero.hpLost = 0;
  // Re-run now that any HP buff is known.
  computePools();

  // EMBARKED. In sea or debark terrain a LAND unit's own attack and defence
  // are REPLACED by a flat 1.0 -- not scaled. Infantry (4.0/5.0) and cavalry
  // (15.0/7.5) deal the identical 20 and 10 against the same target, which no
  // scaling of two different stats can produce.
  const wet = EMBARKED_TERRAIN.includes(myTerrain);
  if (wet) {
    // AIR units are embarked too, not just land ones: 10 fighters in sea
    // terrain deal exactly 1.0 x E(20) = 20.00, the same flat figure infantry
    // and cavalry give. Only a naval unit is at home there.
    // The class token in UNITS is 'sea', not 'naval'. Written as 'naval' this
    // filter matched EVERY unit including the ships, so a battleship in sea
    // terrain fought at a flat 1.0 instead of its measured 40 — a 40x error on
    // the one terrain ships are supposed to be in. Nothing caught it because
    // no test had ever put a naval unit in sea terrain: the embarked tests all
    // used land and air units, which the filter did classify correctly.
    const embarked = rows.filter((r) => r.unit && r.unit.cls !== 'sea');
    for (const r of embarked) r.embarked = true;
    if (embarked.length) {
      caveats.push(`${label}: ${embarked.length} unit row(s) are EMBARKED in `
        + `${myTerrain} terrain. Embarkation is a CLASS CHANGE, not a penalty: `
        + `they attack at a flat 1.0, hold a flat ${EMBARKED_MAXHP} HP each `
        + 'whatever they are, and are hit on the attacker\'s naval column. A '
        + 'heavy tank at sea has ten hit points, the same as a rifleman.');
    }
  }

  // Pools AGAIN, because embarkation replaces per-unit max HP with a flat 10
  // and the flag above is what says which rows it applies to. Computing them
  // before this point drew a heavy tank's 260 for a stack that holds 10.
  if (wet) computePools();

  const primary = rows.length ? rows[0].unit : resolveUnit(cfg && cfg.unit);
  const n = rows.reduce((t, r) => t + r.count, 0);
  const anyPoolUnknown = rows.some((r) => r.pool === null);
  // The hero's own pool is part of the stack's, because the hero is a target
  // that takes a share of every round. Leaving it out made the rows and the
  // stack total disagree by exactly the hero's HP, which the UI's own
  // row-vs-total check caught the moment the hero became a target.
  const heroPool = (side_hero && side_hero.pool) ? side_hero.pool : 0;
  const poolFull = (!rows.length || anyPoolUnknown)
    ? null : rows.reduce((t, r) => t + r.poolFull, 0) + heroPool;
  const poolNow = (!rows.length || anyPoolUnknown)
    ? null : rows.reduce((t, r) => t + r.pool, 0) + heroPool;
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
    // A BUILDING'S HP BAR IS THE TOP LEVEL ONLY, not the whole pool. The game
    // shows a level-4 fortress as "5 / 50" and the site's field agrees: "5"
    // and "10%" produce the identical battle, and "50" and "100%" likewise, so
    // the bar is 0-50 whatever the level and a percentage is a percentage OF
    // THAT BAND. Damage comes off the top, which is why the site reports a
    // battered fortress as a LEVEL plus a top-band figure -- one reading on
    // file has a 250 HP fortress come out of a round as "level 5, 41.5".
    //
    //     pool = (level - 1) x 50 + top-band HP
    //
    // This used to read full x (pct/100), which is the same number at 100% and
    // wrong everywhere else -- and every fortress ever measured here was
    // entered at 100%, so nothing in the record could show it. A level-4
    // fortress at 5/50 came out as 20 HP and 21% damage reduction where the
    // site gives 155 and 61.5%.
    const band = (def.hpPerLevel === null || def.hpPerLevel === undefined)
      ? null : def.hpPerLevel;
    let bHp = null;
    if (full !== null) {
      if (band === null) {
        // Non-uniform levels: no band size to take the percentage on, so the
        // old proportional reading stands and says so.
        bHp = full * (bHpPct / 100);
        if (bHpPct !== 100) {
          caveats.push(`${label}: ${def.label} HP is not uniform per level, so `
            + 'what a partial HP bar means for it was never measured. The '
            + 'percentage is applied to the whole pool, which is how a '
            + 'fortress does NOT behave.');
        }
      } else {
        bHp = Math.max(0, full - band * (1 - bHpPct / 100));
      }
    }
    side.buildings.push({
      code: def.code, label: def.label, level: lvl,
      hpFull: full, hp: bHp,
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
  // Terrain and distance are properties of the BATTLE, not of a side.
  const terrain = (config && typeof config.terrain === 'string')
    ? config.terrain : 'land';
  const distance = Math.max(0, num(config && config.distance, 0));
  // TERRAIN IS PER SIDE. A battleship fights from the sea against infantry on
  // land, and the target's terrain is what decides the coefficient column: the
  // same fighters read 6.0 per effective unit in the air and 40.0 embarked at
  // sea. One shared field cannot express that pairing. It defaults to the
  // attacker's, so every existing single-terrain call behaves as before.
  const defenderTerrain = (config && typeof config.defenderTerrain === 'string')
    ? config.defenderTerrain : terrain;
  // MUTUAL: both stacks attacking each other. The form has always offered it
  // (B.1.target = A.1) and this project never once submitted it, so until now
  // the engine had no way to express half the configurations the page allows.
  const mutual = !!config.mutual;
  const battle = { terrain, defenderTerrain, distance, mutual };
  const atk = makeSide(config.attacker, 'attacker', derivation, caveats, battle);
  const def = makeSide(config.defender, 'defender', derivation, caveats, battle);

  // An embarked row's coefficient depends on what it is shooting at, so each
  // side is told the opposing side's class once. A stack cannot mix classes --
  // the server refuses ground and air in one stack -- so one class per side is
  // the whole answer, not a simplification.
  const defClass = def.rows.length
    ? targetClassFor(atk.rows[0] && atk.rows[0].unit, def.rows[0].unit,
                     battle.defenderTerrain) : null;
  const atkClass = atk.rows.length
    ? combatClass(atk.rows[0].unit, battle.terrain) : null;
  for (const r of atk.rows) r.embarkedTargetClass = defClass;
  for (const r of def.rows) r.embarkedTargetClass = atkClass;

  // A HERO HAS TARGET-CLASS COLUMNS, all twenty-two of them, on both sides.
  // Every land-hero reading in this project fired at INFANTRY, so one number
  // per side looked like the whole story; it is the LAND column and nothing
  // else. Lawrence contributes 45.0 against land, 4.5 against air and 11.25
  // against naval -- a factor of ten from the same hero at the same level --
  // and all sixteen land heroes differ across the three. Richthofen was the
  // first case found and it looked like a quirk of one air hero.
  //
  // The scalar stays the fallback, and for every hero measured it equals the
  // land column, so a battle on land computes exactly as it did.
  // Applied as a RATIO to the column the scalar was read in, not as a
  // replacement. Two heroes have an own attack that moves with level -- 25 to
  // 125 for Richthofen -- and overwriting hero.atk with a level-10 column
  // threw that curve away. The base column is 'land' for every hero measured
  // against infantry, which is all sixteen land ones, and the hero's own class
  // for the air and naval ones, whose curves were read air-against-air.
  const heroCol = (side, cls) => {
    if (!side.hero || !side.hero.def || cls === null) return;
    const t = side.role === 'attacker'
      ? side.hero.def.atkByTargetClass : side.hero.def.defByAttackerClass;
    if (!t || t[cls] === undefined) return;
    const base = side.hero.def.atkColumnBase || 'land';
    if (t[base] === undefined || t[base] === 0) return;
    side.hero.atk *= t[cls] / t[base];
    side.hero.atkColumn = cls;
  };
  heroCol(atk, defClass);
  heroCol(def, atkClass);
  for (const s of [atk, def]) {
    if (s.hero && s.hero.atkColumn && s.hero.atkColumn !== 'land') {
      derivation.push({
        label: `${s.role === 'attacker' ? 'Attacker' : 'Defender'} hero column`,
        formula: `${s.hero.def.label} is fighting ${s.hero.atkColumn} units, and `
          + `a hero has a column per target class exactly as a unit does: `
          + `${round4(s.hero.atk)} here, against `
          + `${round4((s.role === 'attacker' ? s.hero.def.atkByTargetClass
            : s.hero.def.defByAttackerClass)[s.hero.def.atkColumnBase || 'land'])} `
          + `against ${s.hero.def.atkColumnBase || 'land'} units.`,
        value: s.hero.atk,
      });
    }
  }

  const matchup = coverageOfStacks(atk.rows, def.rows,
                                   battle.defenderTerrain, battle.terrain);
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
    reasons.push('Flown as a PATROL. Both sides fire with what survives a fraction of their own '
      + 'losses — the same post-fire law a strike pays in full, charged at a discount — and the '
      + `fraction is ${patrol.c}, fitted across ${PATROL.cellsMeasured} cells on both channels. It `
      + `is not pinned to the printed decimal, so the result stays estimated.`);
    caveats.push(`Patrol attrition is ${patrol.c}, bracketed to ${patrol.range[0]}-`
      + `${patrol.range[1]} over ${PATROL.cellsMeasured} cells — a band a tenth as wide as the one `
      + 'this app shipped, which was an artifact of a survivor rule since corrected. The residual '
      + 'is 0.3-0.5% and confined to air stacks against armoured cars, where the defender\'s own '
      + 'attenuation is largest. Treat the figure as good to about half a per cent.');
  }

  // ---- coefficients --------------------------------------------------------
  const atkCoef = attackCoefficient(atk.unit, def.unit,
                                    battle.defenderTerrain, battle.terrain);
  const defCoef = defenceCoefficient(def.unit, atk.unit,
                                     battle.defenderTerrain, battle.terrain);
  // ATTENUATION IS AGAINST SURFACE TARGETS, land and naval alike -- not land
  // only. A fighter attacking a cruiser deals 65.51 where an unattenuated
  // stack would deal 100.00, and running the post-fire law over both naval
  // targets recovers a single coefficient to four decimals. Air against AIR is
  // NOT attenuated: 20 fighters deal exactly 20.0 x E(20) to bombers while
  // losing 8.75% of their pool, and the attenuated figure would be 18.29.
  //
  // The Balloon is excluded, as it is in patrolMode() for the same reason: on
  // land it is a land unit, and nothing on land is attenuated. It was excluded
  // there and not here, so a balloon attacking two hundred infantry came out
  // at 33.86 against a measured 60.00.
  const atkSurface = atk.unit && def.unit
    && (combatClass(def.unit, battle.defenderTerrain) === 'land'
      || combatClass(def.unit, battle.defenderTerrain) === 'naval');
  const attenuated = !!(atkSurface && atk.unit.cls === 'air'
    && atk.unit.code !== 'bal');

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

  // BUILDING DAMAGE IS PER ROW, not per stack. Every building sweep this
  // project ran used a SINGLE-TYPE stack, and on a single-type stack "one rate
  // times the stack's effective units" and "each row's rate times its own
  // effective units, summed" are the same number -- so nothing in the record
  // could tell them apart, and the cheaper one went in. A real mixed army
  // separates them at once: 35 infantry at 0.30, 6 armoured cars at 1.00 and
  // 17 cavalry at 2.00 deal 38.06 by the row sum, against the 10.41 a single
  // infantry rate gives, and the site prints 38.1.
  //
  // The consequence was not cosmetic. Under-reporting building damage by 3.7x
  // kept a level-4 fortress alive for the whole battle, its damage reduction
  // never decayed, and the engine handed the defender a win the site gives to
  // the attacker.
  const bdRates = atk.rows.map((r) => (r.unit
    ? BUILDING_DAMAGE_PER_EFFECTIVE_UNIT[r.unit.code] : undefined));
  // One unmeasured row makes the whole total unknown. Summing the rest would
  // silently under-report, which is the failure this block already guards
  // against for a single-type stack.
  const bdMissing = atk.rows.filter((r, i) => bdRates[i] === undefined);
  const bdRate = bdMissing.length ? undefined : true;
  if (def.buildings.length && bdRate === undefined) {
    const bdGap = bdMissing[0] && bdMissing[0].unit ? bdMissing[0].unit : atk.unit;
    const floor = BUILDING_DAMAGE_FLOOR[bdGap.code];
    caveats.push(floor
      ? `Damage to buildings from ${bdGap.label} is CENSORED, not unknown: it `
        + `dealt exactly the fortress's whole pool, so ${floor} per effective unit `
        + 'is a floor and not a value. Building damage is withheld rather than '
        + 'quoted as if the reading were complete.'
      : `Damage to buildings has no reading for ${bdGap.label}, and nothing in `
        + 'the model predicts it — the per-unit figures range from 0.30 to 6.00 '
        + 'with no relation to the unit\'s attack value. Building damage is withheld.');
  }

  // ---- rounds --------------------------------------------------------------
  // Patrol treats maxRounds as a DURATION and scales one pass by it (measured:
  // the per-round rate is flat across a 0.25/0.5/0.75/1 ladder). Everything
  // else iterates whole rounds. Looping a fractional count would run zero
  // times and silently return no damage at all.
  // RANGE IS A BINARY GATE. Inside range the figure is identical to zero
  // distance; outside it the server returns no result rows at all — there is
  // no battle. Only three ranges are on record, so an unlisted unit is not
  // gated rather than guessed at.
  // A battle happens if ANY attacking row reaches. The rows that cannot are
  // already marked inert in makeSide and contribute nothing; only when every
  // one of them is out of reach does the server return no result at all.
  const reaching = atk.rows.filter((r) => !r.inert);
  // A HERO FIRES WHEN ITS STACK CANNOT, which this file used to deny flatly.
  // Ten submarines against a target at 10-50 km produce no result rows at all
  // -- until a hero is aboard, and then the target loses 15.00 a round. So the
  // stack being out of range suppresses the STACK, not the battle.
  const heroReach = (atk.hero && HERO_REACH[atk.hero.code]) || null;
  const heroFires = !!heroReach && battle.distance <= heroReach.reach;
  // The ABILITY has its own range, and it is not the hero's. Plain Lucien is
  // silent at 75 km while Lucien-with-gas at level 15 lands its full 40.00
  // there — so at 75 km the reading is the ability with no own attack in it at
  // all, which is exactly what makes that cell a clean total.
  const abilityDef = (atk.hero && BOMBARDMENT[atk.hero.code]) || null;
  const abilityFires = !!abilityDef
    && battle.distance <= bombardmentRange(abilityDef, atk.hero.level);
  const stackOutOfRange = atk.rows.length > 0 && reaching.length === 0;
  const outOfRange = stackOutOfRange && !heroFires && !abilityFires;
  if (stackOutOfRange && heroFires) {
    derivation.push({
      label: 'Stack out of range, hero still firing',
      formula: `Nothing in the attacking stack reaches ${battle.distance} km, but `
        + `${atk.hero.def.label} does — measured: ten submarines at 0 km against a `
        + `target at 10-50 km return no result rows at all with no hero aboard, and `
        + `${round4(atk.hero.atk)} a round with one. Reach for this hero is `
        + `${heroReach.bound}.`,
      value: null,
    });
  }
  if (outOfRange) {
    derivation.push({
      label: 'Out of range',
      formula: `Nothing in the attacking stack reaches ${battle.distance} km. `
        + 'No battle takes place — out of range is not a weaker battle, the '
        + 'server returns no result rows at all (measured: artillery fires at '
        + '50 and not at 51, the railgun at 150 and not at 151, and every '
        + 'melee unit at 5 and not at 6).',
      value: null,
    });
  }

  // FREE BOMBARDMENT. Past 5 km the defender takes its full share and returns
  // nothing. This is a property of the distance, not of what the defender is
  // holding: lart reaching 30 km, a cruiser reaching 40 and a battleship
  // reaching 75 are all silent at 8 km, as is a mixed inf+lart defender at 6.
  const defSuppressed = !outOfRange && battle.distance > MELEE_RANGE;
  if (defSuppressed) {
    caveats.push(`At ${battle.distance} km the defender never fires back. Past `
      + `${MELEE_RANGE} km the attacker takes exactly zero while still dealing `
      + 'its full figure — measured at 6, 7 and 8 km against a defender that '
      + 'reaches thirty.');
    derivation.push({
      label: 'Defender suppressed',
      formula: `${battle.distance} km > ${MELEE_RANGE} km, so the defender `
        + 'deals 0. Light artillery bombarding from 6 km deals 100.00 and '
        + 'loses nothing; from 5 km it deals the same 100.00 and loses 20.00.',
      value: 0,
    });
  }

  // Zero rounds when out of range: both sides take nothing, through the same
  // return path as any other battle rather than a second exit.
  // PATROL ITERATES ROUNDS. It used to compute one round and multiply by the
  // duration, which is right below one round and badly wrong above it: at 100
  // rounds that gives 29811.90 where the server prints 9108.46, a factor of
  // 3.3. Both sides wear each other down, and a stack that has lost most of
  // its pool does not keep dealing its opening figure. Iterating instead
  // reproduces the same ladder to 0.05% at 20 rounds.
  //
  // Below one round the proportionality IS measured -- a 0.25/0.5/0.75/1
  // ladder gives a flat per-round rate -- so a fractional duration scales the
  // single round it runs, and a fractional TAIL scales the last of many.
  const wholeRounds = patrol.applies ? Math.max(1, Math.ceil(rounds)) : rounds;
  const patrolTail = patrol.applies && rounds > 1 ? rounds - Math.floor(rounds) : 0;
  const loopRounds = outOfRange ? 0 : wholeRounds;
  // How many rounds were actually FOUGHT, which is not the number asked for:
  // the loop stops the moment a side's pool is gone. The page needs this so it
  // can say "decided in round 7" rather than making the reader choose a round
  // count they have no way of knowing in advance.
  let roundsFought = 0;
  for (let r = 1; r <= loopRounds; r += 1) {
    const tag = loopRounds > 1 ? `R${r} ` : '';
    // Rounds after the first fight with what is left: fewer units, and those
    // units damaged. Both change the output and neither used to.
    if (r > 1) { refreshRound(atk); refreshRound(def); }
    // A SIDE IS FINISHED WHEN ITS POOL IS GONE, NOT WHEN ITS UNIT COUNT HITS
    // ZERO. `n` counts units and a hero is not one of them, so a stack whose
    // last unit had died while its hero was still standing was called finished
    // and the battle stopped early. On a real army that decided the winner: the
    // defender's twelve armoured cars died in round 9 with Kangal still holding
    // 24.2 HP, this engine stopped there and reported the defender alive, and
    // the site fights on and destroys it.
    //
    // Testing the pool alone is also strictly safe: if every unit is dead and
    // there is no hero, the pool is zero by construction. And a hero with no
    // troops at all is a configuration the source's help page documents --
    // "to use a hero without any troops just keep one unit and give it a count
    // of zero" -- so a stack that is only a hero must be able to fight.
    if (atk.pool <= EPS || def.pool <= EPS) {
      derivation.push({
        label: `${tag}round skipped`,
        formula: 'One side has no surviving HP; the battle is over.',
        value: null,
      });
      break;
    }
    roundsFought = r;

    // The patrol fixed point is per ROUND: each side fires with what survives a
    // fraction of THIS round's losses, and the stacks entering round five are
    // not the stacks that entered round one. Solving once before the loop --
    // which is what happens when a single round is multiplied out — freezes
    // the opening state.
    const patrolScale = !patrol.applies ? 1
      : (rounds < 1 ? rounds
        : (patrolTail > 0 && r === wholeRounds ? patrolTail : 1));
    const patrolSolved = (patrol.applies && patrolScale > 0)
      ? solvePatrol(atk, def, atkCoef.value, defCoef.value, patrol.c) : null;

    // THE HERO'S ABILITY, from the pools as they stand at round start. It runs
    // for a measured number of rounds and then stops: round 7 of a Tōgō strike
    // drops from 56.39 to 14.77, and rounds 10 and 11 of a Lucien strike
    // deliver 8.00 -- the hero's own attack and nothing else.
    const bdef = abilityFires ? abilityDef : null;
    // UNIT pool, not stack pool. side.pool carries the hero's own HP as well,
    // and the measured denominator is the two unit stacks plus ONE extra
    // participant of about 39 HP -- which is the hero row, and is already in
    // BOMBARDMENT_SPLIT.extraPool. Counting the hero's full 120.6 as well put
    // the defender's cut at 55.59 where the server prints 56.39.
    const unitPool = (side) => (side.hero
      ? side.pool - Math.max(0, (side.hero.pool || 0) - (side.hero.hpLost || 0))
      : side.pool);
    const bomb = (bdef && r <= bdef.rounds)
      ? bombardmentRound(bdef, atk.hero.level, battle.distance,
                         unitPool(atk), unitPool(def))
      : null;
    if (bdef && r === bdef.rounds + 1) {
      derivation.push({
        label: `${tag}${bdef.label}'s ability has expired`,
        formula: `It contributes for ${bdef.rounds} rounds (measured), after which `
          + `only the hero's own ${bdef.ownAttack} remains.`,
        value: null,
      });
    }
    if (bomb) {
      derivation.push({
        label: `${tag}${bdef.label} ability`,
        formula: `${round4(bomb.total)} total at level ${atk.hero.level}`
          + `${bomb.exact ? '' : ' (interpolated from the measured rule 5 x level)'}`
          + `, centred on the target. `
          + (bomb.inBlast
            ? `At ${battle.distance} km the attacking stack is inside its own `
              + `${bomb.radius} km blast, so the total is split by HP pool share: `
              + `${round4(bomb.toDef)} to the defender, ${round4(bomb.toAtk)} to the `
              + 'attacker — friendly fire is measured, not inferred'
            : `At ${battle.distance} km the attacker is outside the ${bomb.radius} km `
              + 'blast, so the target absorbs all of it')
          + `${bomb.rExact ? '' : ' (radius interpolated from the measured rungs)'}`,
        value: bomb.toDef,
      });
      if (fort) {
        caveats.push('A fortress and a bombardment ability appear together. Whether '
          + 'fortress DR reduces the ability was never measured; this engine does not '
          + 'reduce it, by analogy with building damage, which IS measured as unreduced.');
      }
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
    // The trench output bonus is applied PER ROW now (infantry only), so it
    // must not also be applied to the whole stack -- that would square it for
    // infantry and invent one for everything else.
    const defParts = defSuppressed
      ? { total: 0, parts: [] }
      : stackOutput(def, (u) => defenceCoefficient(u, atk.unit, battle.defenderTerrain,
                                             battle.terrain).value, patrolScale);
    // PATROL ATTENUATES THE DEFENDER TOO, which this engine did not model at
    // all: it reported 160.00 attacker losses where the server prints 110.46.
    // The per-row decomposition below is left as stackOutput computed it,
    // because the solver works on the stack and no measurement splits it.
    const defOutput = (patrolSolved && patrolSolved.defOutput !== null
      && patrolSolved.defOutput !== undefined)
      ? patrolSolved.defOutput * patrolScale
      : (defParts.total === null ? 0 : defParts.total);
    // The rows have to sum to the stack. The solver works on the whole stack --
    // no measurement splits patrol attenuation per row -- so the per-row
    // figures are scaled to the solved total rather than left as stackOutput
    // computed them. The suite's own row-vs-total check caught this the moment
    // it was skipped, which is exactly what that check is for.
    if (patrolSolved && defParts.total !== null && defParts.total > EPS
        && Math.abs(defParts.total - defOutput) > EPS) {
      const k = defOutput / defParts.total;
      for (const pt of defParts.parts) {
        const before = pt.out;
        pt.out *= k;
        // Rows accumulate, so correct this round's contribution rather than
        // overwriting the running total with one round's figure.
        if (pt.row && typeof pt.row.damageDealt === 'number') {
          pt.row.damageDealt += pt.out - before;
        }
        if (pt.hero && def.hero) def.hero.dealt = pt.out;
      }
    }
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
      formula: defSuppressed
        ? `0 — bombarded from ${battle.distance} km, past the ${MELEE_RANGE} km `
          + 'at which a defender can answer at all'
        : (def.rows.length > 1 || def.hero)
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
    const selfBomb = bomb ? bomb.toAtk : 0;
    // Uncapped here for the same reason: allocate() caps each row against what
    // it has left and drops the surplus, so the side total falls out of the
    // split rather than being imposed on it.
    let atkLostThis = defOutput + selfBomb;
    // Deaths come from the per-row split, because a mixture's rows have
    // different per-unit HP and a stack-level division would be meaningless.
    const atkAlloc = allocate(atk, atkLostThis);
    let atkDeathsThis = 0;
    for (const pt of atkAlloc.parts) {
      const d = deathsFromShare(pt.row, pt.share);
      pt.row.hpLost += pt.share;
      pt.row.deaths += d;
      atkDeathsThis += d;
    }
    // The same on this side, for the same reason. Symmetry is not decoration
    // here: a mutual attack puts the mixture and the hero on the A side too.
    atkLostThis = atkAlloc.parts.reduce((t, pt) => t + pt.share, 0);
    if (atk.rows.length > 1) {
      derivation.push({
        label: `${tag}Attacker damage split across rows`,
        formula: 'in proportion to (target factor x count) — infantry 0.50, '
          + 'cavalry 0.75, everything else 1.00, a hero 0.40: '
          + `${atkAlloc.parts.map((pt) => `${partName(pt.row)} `
            + `${round4(pt.share)}`).join(', ')}`,
        value: atkLostThis,
      });
      if (atkAlloc.overflow) {
        derivation.push({
          label: `${tag}Attacker surplus discarded`,
          formula: 'An attacking row could not absorb its share and the surplus '
            + 'is DROPPED, not passed to the others — see the defender note.',
          value: round4(atkAlloc.discarded),
        });
      }
    }
    if (atkLostThis < defOutput + selfBomb - EPS) {
      derivation.push({
        label: `${tag}Attacker loss capped by its rows`,
        formula: `incoming ${round4(defOutput + selfBomb)} exceeds what the rows can absorb; the `
          + 'stack is wiped. A wiped land stack still deals its full damage (measured).',
        value: atkLostThis,
      });
    }
    derivation.push({
      label: `${tag}Attacker HP lost`,
      formula: `defender output ${round4(defOutput)} split across the rows and capped in each = ${round4(atkLostThis)}`,
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
      atkOutput = patrolSolved.atkOutput === null
        ? null : patrolSolved.atkOutput * patrolScale;
      const loC = solvePatrol(atk, def, atkCoef.value, defCoef.value, patrol.range[0]);
      const hiC = solvePatrol(atk, def, atkCoef.value, defCoef.value, patrol.range[1]);
      derivation.push({
        label: `${tag}Attacker output (patrol)`,
        formula: `Both sides fire with what survives ${patrol.c} of their OWN losses — the same `
          + `post-fire law a strike pays in full, charged at a discount. Each side's losses are `
          + `the other's output, so the pair is solved as a fixed point`
          + `${patrolScale !== 1 ? `, then scaled by ${round4(patrolScale)} rounds` : ''}. `
          + `= ${round4(atkOutput)} [c in ${patrol.range[0]}-${patrol.range[1]} gives `
          + `${round4((loC.atkOutput || 0) * patrolScale)}-${round4((hiC.atkOutput || 0) * patrolScale)}]`,
        value: atkOutput,
      });
      derivation.push({
        label: `${tag}Defender output (patrol)`,
        formula: `The defender is attenuated by the same law and the same fraction. This engine `
          + `did not model that at all and reported 160.00 attacker losses where the server `
          + `prints 110.46 — 45% out, in the direction that makes patrol look worse than it is. `
          + `= ${round4(defOutput)}`,
        value: defOutput,
      });
    } else if (attenuated) {
      const nAlive = atk.n - atkDeathsThis;
      if (nAlive <= 0) {
        // MEASURED: a wiped air stack deals NOTHING. Three tactical bombers at
        // 5% HP are wiped by the defending infantry and the defender loses
        // 0.00 -- which is the opposite of a wiped LAND stack, which still
        // deals its full damage. Ground fire cannot wipe a healthy air stack
        // at all, so the case is only reachable through a damaged one.
        atkOutput = 0;
        derivation.push({
          label: `${tag}Attacker output`,
          formula: 'Zero: the air stack has no survivors, and a wiped AIR stack deals '
            + 'nothing (measured). A wiped LAND stack still deals full damage — the two '
            + 'are different laws, and this is the air one.',
          value: 0,
        });
      } else {
        // THE HERO'S HP IS NOT PART OF THE STACK'S ATTENUATION. atk.pool
        // includes it, because the hero is a target that takes a share of
        // every round -- but the post-fire fraction is about the UNITS. Using
        // the combined pool made von Thaden's 121 HP soften the attenuation
        // and added 53.11 to a bomber stack where the server adds 10.14, which
        // is the hero's own attack and nothing else.
        const heroPool = (atk.hero && atk.hero.pool) ? atk.hero.pool : 0;
        const heroLost = (atk.hero && atk.hero.hpLost) ? atk.hero.hpLost : 0;
        const unitPool = atk.pool - heroPool;
        const unitLost = atkLostThis - Math.min(heroLost, atkLostThis);
        const fAfter = (unitPool - unitLost) / (nAlive * atk.perUnitMaxHP);
        const aliveE = effectiveUnits(nAlive);
        // An air hero fights and buffs on this path too. It was invisible
        // here: the post-fire law is a separate branch that never consulted
        // the hero, so Richthofen and von Thaden did nothing at all on the one
        // terrain they work on.
        const airHeroM = (atk.hero && atk.hero.buffs && atk.unit
          && atk.hero.buffs[atk.unit.code]) ? atk.hero.buffs[atk.unit.code].m : 1;
        // A hero's own attack has TARGET-CLASS columns where it was measured
        // to. Richthofen adds 70.00 to a stack shooting at aircraft and 16.85
        // shooting at infantry -- the same hero at the same level, a factor of
        // four. Reading one column and using it for all three is what made the
        // older 16.80 look like an attenuation artifact of 70.0.
        // hero.atk already carries the target-class column and the hero's own
        // HP scaling, applied once in runSimulation for both paths.
        const airHeroAtk = atk.hero ? (atk.hero.atk || 0) : 0;
        atkOutput = atkCoef.value * aliveE * hpMultiplier(fAfter) * airHeroM
          + airHeroAtk;
        if (atk.hero) {
          atk.hero.dealt = airHeroAtk;
          atk.hero.heroEff = 1;
        }
        derivation.push({
          label: `${tag}Attacker output (post-fire, air vs ground)`,
          formula: `${atkCoef.value} x E(${nAlive})=${round4(aliveE)} x m(${round4(fAfter)})=`
            + `${round4(hpMultiplier(fAfter))}`
            + `${airHeroM !== 1 ? ` x hero ${round4(airHeroM)}` : ''}`
            + `${airHeroAtk ? ` + hero's own ${round4(airHeroAtk)}` : ''}`
            + ` = ${round4(atkOutput)} — an air attacker's output is `
            + 'computed AFTER the round\'s incoming fire (measured: 30 cells, worst residual 0.005 HP)',
          value: atkOutput,
        });
        // This used to escalate to 'estimated' above 20 units, saying that
        // E(survivors) and a per-unit sum of m(f) disagree there and nothing
        // decided between them. They never disagree anywhere: m is affine, so
        // sum_i m(f_i) = s x m(f) identically. Attenuated stacks at 25, 40 and
        // 50 units are reproduced to 0.001% by the law as written, and the
        // rivals that DO differ -- m inside E, or m against the raw count --
        // miss by 0.33% and 42.9%. See PROVENANCE['HP.affine'].
      }
    } else {
      const atkParts = stackOutput(atk, (u) => attackCoefficient(u, def.unit, battle.defenderTerrain,
                                          battle.terrain).value, 1);
      atkOutput = atkParts.total === null ? null : atkParts.total;
      // A HERO DOES NOT SATURATE AGAINST ROWS THAT CANNOT REACH. This file's
      // own range rule says an out-of-range row "neither fires nor counts
      // toward E", but side.n keeps counting it, which never mattered while
      // out-of-range meant no battle at all. It matters now: at fifty
      // submarines the hero's slot came out as E(51)-E(50) = 0 and its 15.00
      // vanished, where the server delivers 15.00 at five, ten, twenty-five,
      // fifty and a hundred alike -- every one of those readings is exactly
      // 15.00 above the ability's share.
      if (stackOutOfRange && atk.hero && atkOutput !== null) {
        // ...and it contributes nothing past its OWN reach, even where its
        // ability still lands: plain Lucien is silent at 75 km.
        const heroAlone = heroFires ? atk.hero.atk : 0;
        atkOutput = heroAlone;
        atk.hero.heroEff = 1;
        atk.hero.dealt = heroAlone;
        derivation.push({
          label: `${tag}Attacker output is the hero alone`,
          formula: `Every unit row is out of range and inert, so the hero does `
            + `not saturate against them: it takes E(1) = 1, not `
            + `E(n+1) - E(n). ${round4(heroAlone)}.`,
          value: heroAlone,
        });
      }
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
              + `m(${round4(pt.row.lastFrac === undefined
                ? pt.row.hpPct / 100 : pt.row.lastFrac)})=${round4(pt.mul)}`
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
      // The ability is additive and is NOT reduced by fortress DR here -- see
      // the caveat pushed above; building damage is the measured precedent.
      // THE FULL SWING GOES TO THE SPLIT, and the caps happen per ROW inside
      // it. This used to cap the total at the side's remaining pool FIRST,
      // which quietly shrank every row's share including the hero's: with 10.5
      // HP of units and a hero on 42.4, a 74.2 swing was cut to 52.9 before
      // being divided, so the hero took 15.1 where the site takes 21.2. The
      // side-level cap is redundant once each row is capped against what it
      // has left -- the sum of the shares cannot exceed the pool by
      // construction -- and it was doing damage on its way to being redundant.
      const delivered = atkOutput * (1 - dr) + (bomb ? bomb.toDef : 0);
      defLostThis = delivered;
      derivation.push({
        label: `${tag}Defender HP lost`,
        formula: dr > 0
          ? `${round4(atkOutput)} x (1 - ${round4(dr)}) = ${round4(delivered)}, split across the rows and capped in each`
          : `attacker output ${round4(atkOutput)}, split across the rows and capped in each`,
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
      const d = deathsFromShare(pt.row, pt.share);
      pt.row.hpLost += pt.share;
      pt.row.deaths += d;
      defDeathsThis += d;
    }
    // WHAT LANDED, not what was swung. The two differ only when a row
    // saturates, and the difference is the whole of the fortress residual:
    // charging the side for damage no row could absorb drove its pool
    // negative and ended the battle a round early.
    defLostThis = defAlloc.parts.reduce((t, pt) => t + pt.share, 0);
    if (def.rows.length > 1 && !def.withheldLoss) {
      derivation.push({
        label: `${tag}Defender damage split across rows`,
        formula: 'in proportion to (target factor x count) — infantry 0.50, '
          + 'cavalry 0.75, everything else 1.00, a hero 0.40: '
          + `${defAlloc.parts.map((pt) => `${partName(pt.row)} `
            + `${round4(pt.share)}`).join(', ')}`,
        value: defLostThis,
      });
      if (defAlloc.overflow) {
        derivation.push({
          label: `${tag}Defender surplus discarded`,
          formula: 'A defending row could not absorb its share and the surplus '
            + 'is DROPPED, not passed to the others — measured on the site\'s own '
            + 'per-round readback (fort_drift): the defender\'s units end round 9 '
            + 'at 0 and its hero at 21.2, having absorbed 31.7 of a ~74 HP swing.',
          value: round4(defAlloc.discarded),
        });
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
      // BUILDING DAMAGE IS ATTENUATED TOO, on the same paths the unit damage
      // is. It was computed from the pre-round stack regardless, which reads
      // 150.00 for five zeppelins where the server prints 147.20. The three
      // fliers' raw figures -- 0.96, 5.80, 29.44 per effective unit -- are the
      // post-fire law applied to buildings; corrected they are 1.00, 6.00 and
      // 30.00 exactly, which is what the table now holds.
      const bdScale = (atkOutput !== null && !defSuppressed
        && (attenuated || patrol.applies))
        ? attenuationFactor(atk, atkLostThis, patrol.applies ? patrol.c : 1)
        : 1;
      // Each row at its OWN rate, its OWN effective units and its OWN HP
      // fraction. The stack-level figures are wrong for a mixture on all three.
      const bdParts = atk.rows.map((r) => {
        const rate = BUILDING_DAMAGE_PER_EFFECTIVE_UNIT[r.unit.code];
        const frac = (r.liveFrac === undefined)
          // liveFrac IS the absolute fraction already -- refreshRound computes it as
      // (pool - hpLost) / (survivors x maxHP), and `pool` is the row's pool
      // AFTER hpPct was applied. Multiplying by hpPct/100 again charged a
      // damaged stack for its opening damage a second time, every round after
      // the first.
      //
      // Invisible in the whole record: every multi-round sweep this project
      // ran started at 100% HP, where hpPct/100 is 1 and the two are the same
      // number. It took a real army -- 35 infantry at 453.6 of 700 -- to
      // separate them. The engine had infantry firing at m=0.438 in round 2
      // where the site gives 0.649.
      ? r.hpPct / 100 : r.liveFrac;
        return { row: r, rate, out: rate * r.effective * hpMultiplier(frac) };
      });
      const bDmg = bdParts.reduce((t, x) => t + x.out, 0) * bdScale;
      const target = def.buildings[0];
      derivation.push({
        label: `${tag}Damage to ${target.label}`,
        formula: (atk.rows.length > 1
          ? `per row: ${bdParts.map((x) => `${x.row.unit.code} ${x.rate}`
            + ` x ${round4(x.row.effective)}`).join(' + ')}`
          : `${bdParts[0].rate} per effective unit x E(${atk.n})=${round4(atkE)}`)
          + `${bdScale !== 1 ? ` x post-fire ${round4(bdScale)}` : ''} = ${round4(bDmg)} — `
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

    // ------------------------------------------------------------------
    // ENGAGEMENT 2 — mutual attacks only.
    // ------------------------------------------------------------------
    // Everything above this line is ONE engagement: A attacks with its attack
    // column and B answers with its defence column, both from the pre-round
    // state. That is the only configuration this project ever submitted --
    // duel() is the only thing in the rig that ever set a B-side target and it
    // always set 0 -- so for its whole life the app could not express a battle
    // in which both stacks are attacking each other.
    //
    // The form has always offered it, and the site's help page says it is not
    // cosmetic: "If two stacks are each attacking the other it makes a
    // difference which side they are on. Army A will always attack first."
    //
    // Measured, that is exactly two engagements in order. A attacks; the
    // stacks are updated; then B attacks with what survived, using ITS attack
    // column against A's defence column. Sixteen cells across a roster whose
    // attack and defence figures disagree by up to four times and in both
    // directions were predicted from this before being submitted, and every
    // one came back to the printed decimal.
    //
    // The side letter is worth a whole stack: ten light artillery facing a
    // hundred infantry are destroyed in engagement 1 and never fire at all,
    // where a DEFENDING stack that is wiped still deals its full figure
    // (measured, and unchanged). Holding the A slot saves a hundred infantry
    // 59.44 HP against ten stormtroopers -- 226.12 instead of 285.56.
    if (battle.mutual && !outOfRange && !def.withheldLoss) {
      refreshRound(atk);
      refreshRound(def);
      const bothAlive = def.pool > EPS && def.n > 0 && atk.pool > EPS && atk.n > 0;
      if (!bothAlive) {
        derivation.push({
          label: `${tag}Engagement 2 does not happen`,
          formula: (def.pool <= EPS || def.n <= 0)
            ? 'The B stack was destroyed in engagement 1, so it never fires. '
              + 'A DEFENDING stack that is wiped still deals its full figure; '
              + 'one that was attacking and died first deals nothing. That is '
              + 'what the side letter buys.'
            : 'The A stack is gone, so there is nothing left for B to fire at.',
          value: null,
        });
      } else {
        // B attacks now, so the coefficients swap sides with the roles.
        const e2Atk = stackOutput(def, (u) => attackCoefficient(
          u, atk.unit, battle.terrain, battle.defenderTerrain).value, 1);
        const e2Def = stackOutput(atk, (u) => defenceCoefficient(
          u, def.unit, battle.terrain, battle.defenderTerrain).value, 1);
        const e2AtkOut = e2Atk.total === null ? null : e2Atk.total;
        const e2DefOut = e2Def.total === null ? null : e2Def.total;
        if (e2AtkOut === null || e2DefOut === null) {
          atk.withheldLoss = true;
          derivation.push({
            label: `${tag}Engagement 2 withheld`,
            formula: 'One of the two columns engagement 2 needs has no measured '
              + 'value for this pairing, so its damage is unknown — not zero.',
            value: null,
          });
        } else {
          const aLost = Math.min(e2AtkOut, atk.pool);
          const bLost = Math.min(e2DefOut, def.pool);
          derivation.push({
            label: `${tag}Engagement 2: B attacks`,
            formula: `B fires with what survived engagement 1 — `
              + `${round4(e2AtkOut)} against A, answered by A's DEFENCE column `
              + `for ${round4(e2DefOut)}. Measured: this is a second whole `
              + 'engagement, not a return volley.',
            value: aLost,
          });
          for (const [side, amount] of [[atk, aLost], [def, bLost]]) {
            const alloc = allocate(side, amount);
            let died = 0;
            for (const pt of alloc.parts) {
              const d2 = deathsFromShare(pt.row, pt.share);
              pt.row.hpLost += pt.share;
              pt.row.deaths += d2;
              died += d2;
            }
            side.hpLost += amount;
            side.pool -= amount;
            side.deaths += died;
          }
          atk.damageDealt += bLost;
          atk.outputRaw += e2DefOut;
          def.damageDealt += aLost;
          def.outputRaw += e2AtkOut;
          for (const side of [atk, def]) {
            if (side.pool <= EPS) { side.pool = 0; side.wiped = true; side.n = 0; }
            else side.n = Math.max(0, side.n0 - side.deaths);
          }
        }
      }
      if (fort || def.buildings.length || atk.hero || def.hero) {
        caveats.push('Engagement 2 of a mutual attack is modelled from the unit '
          + 'columns only. No mutual reading on record carries a fortress, a '
          + 'building or a hero, so what those do in the second engagement is '
          + 'not measured and is not applied there.');
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
    // `asked` is what was requested; `fought` is what happened. They differ the
    // moment a side is destroyed, and `decided` says the battle ended on its
    // own rather than running out of rounds.
    rounds: {
      asked: rounds,
      fought: roundsFought,
      decided: !!(atk.wiped || def.wiped),
      ranOut: !(atk.wiped || def.wiped) && roundsFought >= Math.floor(loopRounds),
    },
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
    // WHERE A HERO SITS IS NOT A PROPERTY OF THE HERO. It is the same
    // strongest-first saturation the units obey, with the hero's own
    // coefficient as its rank: a hero that out-damages every row saturates
    // first and takes E(1) = 1, one that does not takes what is left,
    // E(n+1) - E(n).
    //
    // It was declared per hero, and for the sixteen land heroes the declared
    // value happens to match what the rank gives -- which is why it went
    // unnoticed. The six air and naval heroes break both ways within the same
    // sweep: Richthofen at 25.0 defending outranks a bomber's 3.0 and sits
    // first, while von Thaden at 10.0 sits behind a fighter's 20.0. Declaring
    // 'first' for both put von Thaden's contribution at 10.00 where the server
    // prints 9.83, and Tōgō's at 15.00 where it prints 14.75.
    const strongest = side.rows.reduce((m2, r) => {
      const c = coefFor(r.unit);
      return (typeof c === 'number' && c > m2) ? c : m2;
    }, -Infinity);
    const heroFirst = hero.atk >= strongest;
    hero.satFirst = heroFirst;
    if (heroFirst) {
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
    // An embarked row's own column, not one flat number. EMBARKED_COEF is
    // the land cell; against air it is 0.5, and using 1.0 there doubled it.
    const c = r.embarked
      ? (EMBARKED_ATTACK[r.embarkedTargetClass] === undefined
        ? EMBARKED_COEF : EMBARKED_ATTACK[r.embarkedTargetClass])
      : coefFor(r.unit);
    if (c === null || c === undefined) return { total: null, parts: [] };
    const frac = (r.liveFrac === undefined)
      // liveFrac IS the absolute fraction already -- refreshRound computes it as
      // (pool - hpLost) / (survivors x maxHP), and `pool` is the row's pool
      // AFTER hpPct was applied. Multiplying by hpPct/100 again charged a
      // damaged stack for its opening damage a second time, every round after
      // the first.
      //
      // Invisible in the whole record: every multi-round sweep this project
      // ran started at 100% HP, where hpPct/100 is 1 and the two are the same
      // number. It took a real army -- 35 infantry at 453.6 of 700 -- to
      // separate them. The engine had infantry firing at m=0.438 in round 2
      // where the site gives 0.649.
      ? r.hpPct / 100 : r.liveFrac;
    const mm = mulEach ? mulEach(r) : hpMultiplier(frac);
    // The stack-level multipliers (trench output, patrol duration) must be
    // carried onto the ROWS as well, or the rows no longer sum to the stack.
    // They did not, and the UI's row-vs-total sanity check caught it: a
    // defender on trench 10 reported rows totalling 141.67 against a stack
    // figure of 218.17, the same number times the 1.54 trench bonus.
    const out = c * r.effective * unitScale * mm * mFor(r.unit) * k
      * (r.trenchOutput === undefined ? 1 : r.trenchOutput);
    // Record the fraction m() was actually given. The derivation used to print
    // r.hpPct/100 beside a multiplier computed from liveFrac, so the line read
    // "m(0.648)=0.438" -- a mismatch that was itself a bug for months, and the
    // thing that finally gave it away.
    r.lastFrac = frac;
    // ACCUMULATE ACROSS ROUNDS. This assigned, so after a three-round battle
    // every row carried its LAST round's damage while the stack total carried
    // all three -- rows summing to 123.46 against a stack of 508.25. The
    // row-vs-stack invariant only caught it once patrol became multi-round,
    // because patrol was the only multi-round case in that check.
    r.damageDealt = (typeof r.damageDealt === 'number' ? r.damageDealt : 0) + out;
    total += out;
    parts.push({ row: r, coef: c, mul: mm, out, heroM: mFor(r.unit) });
  }
  return { total, parts };
}

/**
 * Split incoming damage across a stack's rows -- and its hero -- in proportion
 * to (target factor x count), then take deaths per row from that row's own
 * per-unit HP. See allocationWeights for what replaced the old rule and why.
 */
/** Row or hero, whichever this allocation part points at. */
/**
 * Re-open each row for a new round: living units, and the fraction of THEIR
 * own maximum that is left. Both feed the next round's output.
 *
 * Measured over an eight-rung maxRounds ladder (50 infantry a side, which
 * lasts seven rounds). The survivor count is WHOLE units -- floor(HP lost /
 * per-unit HP) -- and m(f) then applies to what those survivors have left,
 * f = remaining pool / (survivors x per-unit max). That fits to 0.042%.
 * Fractional survivors without m(f) fits 0.221%, whole survivors without m(f)
 * 1.063%, and evaluating post-fire as air does 6.0%.
 *
 * The engine used to compute each row's effective count ONCE and never update
 * it, which is the "fixed E" law: 13.66% out by round six, where it declared a
 * wipe that does not happen.
 */
/**
 * How many whole units a round's damage destroys.
 *
 * NOT floor(damage / max HP). A round's casualties are counted against what
 * the surviving units actually have left -- the stack's remaining pool divided
 * between them -- so a battered stack loses units faster than its paper HP
 * suggests. Fitting the max-HP rule to a 50-a-side ladder on five unit types
 * missed the printed death count in 27 of 40 cells and drifted the HP figures
 * up to 0.970%; this rule is exact on all 40 deaths and 0.0032% on HP.
 *
 * The explanation that stood before this was that high per-unit HP made the
 * survivor count coarse, so heavy tanks drifted and infantry did not. That was
 * written from one unit type and the ladder disproves it: at 40 HP the
 * stormtrooper is exact through eight rounds while the armoured car at 60 is
 * the worst in the roster and infantry at 20 drifts too. The error never
 * tracked per-unit HP at all -- it tracked how many rounds both sides survived.
 *
 * A stack whose remaining pool reaches zero loses every unit, which the
 * division alone does not give: the last round's floor leaves one standing.
 */
function deathsFromShare(row, share) {
  if (!row.perUnitMaxHP) return 0;
  const alive = Math.max(0, row.count - row.deaths);
  if (alive <= 0) return 0;
  const remaining = row.pool - row.hpLost;
  if (remaining - share <= EPS) return alive;      // wiped: all of them
  if (remaining <= 0) return 0;
  return Math.min(alive, Math.floor(share / (remaining / alive)));
}

/**
 * How much a stack's output is scaled down by the damage it took this round.
 * The post-fire law expressed as a ratio, so building damage can be charged
 * the same discount the unit damage is without duplicating the arithmetic.
 * c is 1 for a strike and the patrol fraction for a patrol.
 */
function attenuationFactor(side, lostThis, c) {
  const hp = side.perUnitMaxHP;
  if (!hp || side.n <= 0) return 1;
  const L = c * lostThis;
  const surv = side.n - Math.floor(L / hp);
  if (surv <= 0) return 0;
  const before = effectiveUnits(side.n) * hpMultiplier(stackFraction(side));
  if (before <= 0) return 1;
  const after = effectiveUnits(surv)
    * hpMultiplier(Math.max(0, Math.min(1, (side.pool - L) / (surv * hp))));
  return after / before;
}

/**
 * PATROL, both sides. Each fires with what survives a fraction c of its OWN
 * losses that round -- the ordinary post-fire law, charged at a discount --
 * and because each side's losses are the other's output, the pair is a fixed
 * point rather than a sequence.
 *
 * The app modelled half of this. It attenuated the attacker with a
 * multiplicative (1 - c x lossFraction) and left the DEFENDER unattenuated,
 * which reported 160.00 attacker losses against a measured 110.46 -- 45% out,
 * in the direction that makes patrol look worse than it is. A single c fits
 * BOTH channels across 24 cells to 0.42% worst, and most of them under 0.1%.
 *
 * Sixty iterations is far past convergence; the map is a contraction because
 * c < 1 and each output is monotone in the other side's loss.
 */
function solvePatrol(atk, def, atkCoef, defCoef, c) {
  const fire = (side, coef, lost) => {
    if (coef === null || coef === undefined) return null;
    const hp = side.perUnitMaxHP;
    if (!hp || side.n <= 0) return 0;
    const L = c * lost;
    const surv = side.n - Math.floor(L / hp);
    if (surv <= 0) return 0;
    const f = Math.max(0, Math.min(1, (side.pool - L) / (surv * hp)));
    return coef * effectiveUnits(surv) * hpMultiplier(f);
  };
  let atkLost = 0;
  let defLost = 0;
  for (let i = 0; i < 60; i += 1) {
    const a = fire(atk, atkCoef, atkLost);
    const d = fire(def, defCoef, defLost);
    if (a === null || d === null) return { atkOutput: a, defOutput: d };
    atkLost = d;
    defLost = a;
  }
  return { atkOutput: fire(atk, atkCoef, atkLost), defOutput: fire(def, defCoef, defLost) };
}

function refreshRound(side) {
  for (const r of side.rows) {
    if (!r.perUnitMaxHP) continue;
    // SURVIVORS ARE COUNT MINUS DEATHS, and deaths are counted round by round
    // as the damage lands (see deathsFromShare). Recomputing them here as
    // floor(cumulative damage / max HP) gives a DIFFERENT number, because a
    // round's damage is measured against what the survivors have left rather
    // than against a full unit. Solving each measured round's output for the
    // survivor count it implies puts it on count-minus-deaths in 20 of 21
    // cells and on the floor rule in 8.
    const alive = Math.max(0, r.count - r.deaths);
    r.liveCount = alive;
    const full = alive * r.perUnitMaxHP;
    r.liveFrac = full > 0 ? Math.min(1, (r.pool - r.hpLost) / full) : 0;
  }
  // THE HERO WEARS DOWN TOO. Its own output scales with its own HP by the same
  // m(f) a unit obeys -- that much was measured -- but the multiplier was
  // baked in once at setup from the hero's OPENING HP and never revisited, so
  // a hero fired at full strength all battle however battered it got.
  //
  // Invisible in the record: every hero reading on file is a single round, and
  // in round one the opening HP IS the current HP. It took the server's own
  // per-round readback to separate them -- at round two the site has Kangal on
  // 79.5 of 90 and contributing 20 x m(0.8833) = 17.78, where this engine was
  // still charging 20 x m(83.1/90) = 18.54.
  if (side.hero && side.hero.poolFull > 0) {
    const heroLeft = Math.max(0, side.hero.pool - (side.hero.hpLost || 0));
    side.hero.atk = side.hero.atkFull
      * hpMultiplier(heroLeft / side.hero.poolFull);
  }
  const live = side.rows.map((r) => ({
    unit: r.unit,
    inert: r.inert,
    count: r.liveCount === undefined ? r.count : r.liveCount,
  }));
  const eff = effectiveByRow(live, side.role === 'attacker' ? 'atk' : 'def');
  side.rows.forEach((r, i) => { r.effective = eff[i].effective; });
}

function partName(t) {
  return t && t.unit ? t.unit.code : (t && t.def ? t.def.label : 'hero');
}

function allocate(side, incoming) {
  // A HERO IS A TARGET. It has its own HP pool and it takes a share of every
  // round like any row, at a weight of 0.40 -- the same constant for all
  // sixteen, independent of its attack, its pool and its level. Leaving it out
  // of the split over-charged every unit row by its share.
  const targets = side.rows.slice();
  const w = allocationWeights(side.rows);
  if (side.hero && side.hero.pool) {
    targets.push(side.hero);
    w.push(HERO_ALLOC_WEIGHT);
  }
  const sum = w.reduce((a, b) => a + b, 0);
  const out = [];
  let discarded = 0;
  targets.forEach((r, i) => {
    const want = sum > 0 ? incoming * (w[i] / sum) : incoming / (targets.length || 1);
    // AGAINST WHAT IS LEFT, not against what the row started with. This read
    // r.pool -- the row's FULL pool -- so a row already down to 15 HP would
    // happily absorb 49 more, and the surplus came out of the side's total as
    // if it had landed. On a single-row side it never showed: the incoming
    // total is capped at the side's remaining pool before it gets here, so
    // `want` could not exceed what was left anyway. It takes a mixture, or a
    // hero, for a row to saturate while the side has HP elsewhere.
    const left = r.pool === null ? null : Math.max(0, r.pool - (r.hpLost || 0));
    const got = Math.min(want, left === null ? want : left);
    discarded += want - got;
    out.push({ row: r, share: got });
  });
  // THE SURPLUS IS DISCARDED, NOT PASSED ON, and that is measured now.
  //
  // This used to hand a saturated row's remainder to the others, with a
  // caveat admitting no measured mixture had ever saturated a row. It has now:
  // the real army's twelve armoured cars enter round 9 with 10.5 HP between
  // them and Kangal on 42.4, and the site's own readback has the units at 0
  // and the hero at 21.2 afterwards -- 31.7 HP applied out of the ~74 the
  // attacker swung. Redistributing instead killed the hero in the same round,
  // ended the battle one round early, and left the fortress 6.17 HP short of
  // the destruction the site reports. The isolated version is starker still:
  // six heavy tanks against five infantry, a hero and a level-5 fortress take
  // the fortress to 208.3 on the site and 157.78 here, purely because the
  // hero soaked a round's worth of surplus it should never have seen.
  //
  // A round's swing is therefore an UPPER BOUND on what it can take off a
  // side, and each row is its own bound within that.
  return { parts: out, discarded, overflow: discarded > EPS };
}


// ---------------------------------------------------------------------------
// THE RECOVERY BILL
// ---------------------------------------------------------------------------
// The server prints eleven summary columns; the app modelled two of them. The
// other nine are the cost and the time to put the stack back together, and
// both are linear in UNIT EQUIVALENTS -- whole units' worth destroyed -- not in
// HP lost. See the long note over REPAIR_COST in data.js for the two readings
// that separate those (the trench sweep, and a 10%-HP stack billing the same
// as a healthy one).
//
// A row that cannot report its loss, or its pool, contributes null rather than
// zero: rule 2 of this module. A partial bill would read as a complete one.
function repairBill(rows) {
  const res = { food: 0, fish: 0, iron: 0, wood: 0, coal: 0, oil: 0, gas: 0, cash: 0 };
  let hours = 0;
  let unknown = false;
  let equivalents = 0;
  for (const r of rows) {
    if (r.hpLost === null || r.hpLost === undefined) { unknown = true; continue; }
    if (r.pool === null || r.pool === undefined || !(r.pool > 0)) {
      if (r.hpLost > 0) unknown = true;
      continue;
    }
    // ue = HP lost / current per-unit HP. For a hero the row IS one unit.
    const ue = r.hpLost / (r.pool / (r.isHero ? 1 : (r.count || 1)));
    equivalents += ue;
    if (r.isHero) {
      // Measured on two heroes; costs time but no resources.
      hours += HERO_REPAIR.hours * ue;
      continue;
    }
    const cost = REPAIR_COST[r.unit];
    const t = REPAIR_HOURS[r.unit];
    if (!cost || !t) { unknown = true; continue; }
    for (const k of Object.keys(res)) res[k] += (cost[k] || 0) * ue;
    hours += t.hours * ue;
  }
  if (unknown) return null;
  const out = {};
  for (const k of Object.keys(res)) out[k] = Math.round(res[k]);
  // Floored ONCE over the stack total, not per row -- the two-row 62-hour
  // reading in the corpus is what pins that.
  out.hours = Math.floor(hours);
  out.unitEquivalents = equivalents;
  return out;
}


// ---------------------------------------------------------------------------
// A HERO'S BOMBARDMENT ABILITY
// ---------------------------------------------------------------------------
// Not to be confused with this file's older use of the word: "free
// bombardment" below is the past-5-km rule under which a defender cannot
// answer. This is Tōgō-with-bombardment and Lucien-with-gas, which were
// recorded as heroes with an unstable own attack and are nothing of the kind.
// They carry a SECOND damage source, centred on the target, divided among
// everything standing in its blast -- which is exactly why its apparent size
// moved with the unit counts on BOTH sides. See the note over BOMBARDMENT in
// data.js for how it was measured.
//
// Two things about the geometry read backwards and both are measured. The
// radius is centred on the TARGET, so the target is hit at any distance; what
// the radius decides is who ELSE is caught. And the attacker's own stack is
// one of those -- so moving the target from 40 km to 50 km RAISES its losses,
// because past 40 the attacker steps out of its own blast and the target
// absorbs the whole thing.

/** The ability's total at a level, from the measured table or its rule. */
function bombardmentTotal(bdef, level) {
  const lv = Math.max(1, Math.round(level || 1));
  if (bdef.totalByLevel[lv] !== undefined) {
    return { total: bdef.totalByLevel[lv], exact: true };
  }
  // Only Tōgō has gaps (11-14, 16-19); its rule is 5 x level from level 3 up,
  // measured at twelve levels including both ends of the range.
  return { total: 5 * lv, exact: false };
}

/** How far the ability can be AIMED — distinct from the radius it splashes over. */
function bombardmentRange(bdef, level) {
  if (typeof bdef.range === 'number') return bdef.range;
  const lv = Math.max(1, Math.round(level || 1));
  const rungs = Object.keys(bdef.rangeByLevel).map(Number).sort((a, b) => a - b);
  let below = rungs[0];
  for (const rg of rungs) if (rg <= lv) below = rg;
  return bdef.rangeByLevel[below];
}

/** The radius at a level. Tōgō's is flat; Lucien's grows, measured at 1, 5, 10, 15. */
function bombardmentRadius(bdef, level) {
  if (typeof bdef.radius === 'number') return { radius: bdef.radius, exact: true };
  const lv = Math.max(1, Math.round(level || 1));
  const rungs = Object.keys(bdef.radiusByLevel).map(Number).sort((a, b) => a - b);
  if (bdef.radiusByLevel[lv] !== undefined) {
    return { radius: bdef.radiusByLevel[lv], exact: true };
  }
  let below = rungs[0];
  for (const rg of rungs) if (rg <= lv) below = rg;
  return { radius: bdef.radiusByLevel[below], exact: false };
}

/**
 * One round of the ability, from the stacks as they stand at round start.
 *
 * Split by HP POOL share over everything in the blast. The attacking side
 * carries one extra participant -- its own hero row -- and including it is
 * what makes this exact rather than merely close: ten submarines against
 * fifty put the target's cut at 41.67 on a bare two-stack pool split, and the
 * server prints 41.39, which is what the same sum gives with the hero's ~39 HP
 * in the denominator.
 */
function bombardmentRound(bdef, level, distance, atkPool, defPool) {
  const { total, exact } = bombardmentTotal(bdef, level);
  const { radius, exact: rExact } = bombardmentRadius(bdef, level);
  const inBlast = distance <= radius;
  const out = { total, toDef: total, toAtk: 0, radius, inBlast, exact, rExact };
  if (!inBlast) return out;
  // Per hero: 39.2 for Tōgō, 16.1 for Lucien. That they differ is the evidence
  // that this is the hero's own row in the blast and not a constant.
  const extra = (typeof bdef.extraPool === 'number')
    ? bdef.extraPool : BOMBARDMENT_SPLIT.extraPool;
  const denom = atkPool + defPool + extra;
  if (!(denom > 0)) return out;
  out.toDef = total * (defPool / denom);
  out.toAtk = total * ((atkPool + extra) / denom);
  return out;
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
      unitsLeft: null, damageDealt: null, wiped: false, repair: null,
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
  // The hero is a target with its own pool, and it now reports what it took.
  // It never reports DEATHS: no hero row on record has ever carried a death
  // count, so null rather than 0 -- zero would be a claim.
  const heroRow = side.hero ? [{
    unit: side.hero.code,
    label: side.hero.def.label,
    isHero: true,
    level: side.hero.level,
    count: 1,
    hpPct: 100,
    effective: side.hero.heroEff === undefined ? null : side.hero.heroEff,
    pool: side.hero.pool === undefined ? null : side.hero.pool,
    hpLost: side.hero.hpLost === undefined ? null : side.hero.hpLost,
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
  // The variance band. simulateVariance rolls ONE uniform +/-10% per side per
  // round, not per unit -- 60 samples give sd 5.285 where a single roll
  // predicts 5.774 and a per-unit roll 1.291. So the whole stack moves
  // together and a big stack cannot average its luck away: the band is the
  // full +/-10%, whatever the stack size.
  const band = (v) => (v === null || v === undefined
    ? null : [v * VARIANCE_BAND.lo, v * VARIANCE_BAND.hi]);
  return {
    rows: rowsOut,
    repair: lossUnknown ? null : repairBill(rowsOut),
    pool: poolStart,
    hpLost: lossUnknown ? null : side.hpLost,
    hpLostBand: lossUnknown ? null : band(side.hpLost),
    damageDealtBand: side.withheldDealt ? null : band(side.damageDealt),
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
