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
  const unit = resolveUnit(cfg && cfg.unit);
  const n = Math.max(0, Math.floor(num(cfg && cfg.count, 0)));
  const hpPct = Math.min(100, Math.max(0, num(cfg && cfg.hpPct, 100)));
  const tf = trenchFactors(cfg && cfg.trench);
  const label = role === 'attacker' ? 'Attacker' : 'Defender';

  const side = {
    role, label, unit, n0: n, n, hpPct, tf,
    perUnitMaxHP: null, poolFull: 0, pool: 0,
    hpLost: 0, deaths: 0, damageDealt: 0, outputRaw: 0, wiped: false,
    buildings: [],
    damageToBuildings: null,
  };

  if (unit && unit.maxHP !== null) {
    side.perUnitMaxHP = unit.maxHP * tf.pool;
    side.poolFull = n * side.perUnitMaxHP;
    side.pool = side.poolFull * (hpPct / 100);
    derivation.push({
      label: `${label} per-unit max HP`,
      formula: tf.pool === 1
        ? `${unit.label} max HP = ${unit.maxHP}`
        : `${unit.maxHP} x trench pool ${tf.pool} = ${round4(side.perUnitMaxHP)}`,
      value: side.perUnitMaxHP,
    });
    derivation.push({
      label: `${label} HP pool`,
      formula: `${n} units x ${round4(side.perUnitMaxHP)} HP x ${hpPct}% = ${round4(side.pool)}`,
      value: side.pool,
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

  const matchup = coverageOf(atk.unit, def.unit);
  let level = matchup.level;
  const reasons = [matchup.reason];

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
    // MEASURED: a direct air strike delivers once, whatever maxRounds says.
    // 30.03 per unit at every rung of the same ladder.
    if (rounds !== 1) {
      caveats.push(`A direct air strike IGNORES maxRounds — the same ladder returned 30.03 per unit `
        + `at 0.25, 0.5, 0.75 and 1 alike. The ${rounds} you asked for changes nothing; one strike `
        + 'is computed. Switch to patrol if you want damage to scale with time on station.');
    }
    derivation.push({
      label: 'Mode: DIRECT STRIKE',
      formula: 'maxRounds is ignored for terrain=air (measured: byte-identical results at '
        + '0.25/0.5/0.75/1). One strike is delivered.',
      value: 1,
    });
    rounds = 1;
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
      coverage: { level, reason: reasons.join(' '), caveats },
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
    const defOutput = defCoef.value * defE * hpMultiplier(defF) * def.tf.output * patrolScale;
    derivation.push({
      label: `${tag}Defender output`,
      formula: `${defCoef.value} x E(${def.n})=${round4(defE)} x m(${round4(defF)})=`
        + `${round4(hpMultiplier(defF))}${def.tf.output !== 1 ? ` x trench ${def.tf.output}` : ''}`
        + `${patrolScale !== 1 ? ` x ${round4(patrolScale)} rounds on station` : ''} = ${round4(defOutput)}`,
      value: defOutput,
    });

    // 2. Attacker takes it. No fortress on the attacking side does anything
    //    in this model, because nobody has measured one.
    const atkLostThis = Math.min(defOutput, atk.pool);
    const atkDeathsThis = Math.floor(atkLostThis / atk.perUnitMaxHP);
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
      atkOutput = atkCoef.value * atkE * hpMultiplier(atkF);
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
    const defDeathsThis = Math.floor(defLostThis / def.perUnitMaxHP);
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
    coverage: { level, reason: reasons.join(' '), caveats },
    derivation,
  };
}

function sideResult(side, withheld) {
  const poolStart = side.poolFull === null ? null : side.poolFull * (side.hpPct / 100);
  if (withheld) {
    return {
      pool: poolStart, hpLost: null, pctLost: null, deaths: null,
      unitsLeft: null, damageDealt: null, wiped: false,
      outputRaw: null, damageToBuildings: null,
      buildings: side.buildings,
    };
  }
  // A side whose loss could not be computed reports null, never 0. Zero would
  // be the engine asserting it took no damage, which is an invention.
  const lossUnknown = !!side.withheldLoss;
  return {
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
